# Database layer — all PostgreSQL reads and writes for incidents, tasks, and teams
import psycopg2
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


def connect_to_database():
    """Open a PostgreSQL connection."""
    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return connection
    except psycopg2.OperationalError as error:
        print(f"❌ Cannot connect to database: {error}")
        print("   Make sure PostgreSQL is running and .env settings are correct!")
        raise


def load_teams_from_file(teams_list):
    """Seed teams table from JSON if empty."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        # Skip seeding if teams already exist
        cursor.execute("SELECT COUNT(*) FROM teams")
        count = cursor.fetchone()[0]
        
        if count > 0:
            return
        
        # Insert each team from the JSON roster
        for team in teams_list:
            cursor.execute(
                """
                INSERT INTO teams (id, name, type, location, capabilities, personnel)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    team["id"],
                    team["name"],
                    team["type"],
                    team.get("location"),
                    ", ".join(team.get("capabilities", [])),
                    team.get("personnel", 1)
                )
            )
        
        connection.commit()
        
    finally:
        cursor.close()
        connection.close()


def get_available_teams():
    """Return teams with status 'available'."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            """
            SELECT id, name, type, location, capabilities, personnel
            FROM teams
            WHERE status = 'available'
            ORDER BY id
            """
        )
        
        teams = []
        for row in cursor.fetchall():
            teams.append({
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "location": row[3],
                "capabilities": row[4],
                "personnel": row[5]
            })
        
        return teams
        
    finally:
        cursor.close()
        connection.close()


def get_recent_incidents(limit=5):
    """Return formatted string of recent incidents for AI context."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            """
            SELECT id, category, severity, status, description
            FROM incidents
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,)
        )
        
        rows = cursor.fetchall()
        
        if not rows:
            return "No incidents yet."
        
        # Format as a readable list for the AI prompt
        lines = []
        for row in rows:
            incident_id, category, severity, status, description = row
            short_desc = description[:80] if description else ""
            lines.append(
                f"ID:{incident_id} | {category} | {severity} | [{status}] | {short_desc}"
            )
        
        return "\n".join(lines)
        
    finally:
        cursor.close()
        connection.close()


def save_new_incident(description, category, severity, location, risks, feed_id=None):
    """Insert a new incident and return its ID."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        risks_text = ", ".join(risks) if risks else ""
        
        cursor.execute(
            """
            INSERT INTO incidents (description, category, severity, location, risks, feed_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (description, category, severity, location, risks_text, feed_id)
        )
        
        incident_id = cursor.fetchone()[0]
        
        connection.commit()
        
        return incident_id
        
    finally:
        cursor.close()
        connection.close()


def save_incident_update(incident_id, update_text, event_type):
    """Record an update on an existing incident."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        # Auto-increment update number per incident
        cursor.execute(
            """
            SELECT COALESCE(MAX(update_number), 0)
            FROM incident_updates
            WHERE incident_id = %s
            """,
            (incident_id,)
        )
        next_number = cursor.fetchone()[0] + 1
        
        cursor.execute(
            """
            INSERT INTO incident_updates (incident_id, update_text, event_type, update_number)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (incident_id, update_text, event_type, next_number)
        )
        
        update_id = cursor.fetchone()[0]
        connection.commit()
        
        return update_id
        
    finally:
        cursor.close()
        connection.close()


def get_incident_history(incident_id):
    """Load full incident history including tasks and assignments."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            "SELECT description, severity FROM incidents WHERE id = %s",
            (incident_id,)
        )
        row = cursor.fetchone()
        if not row:
            return {}
        
        original_description, original_severity = row
        
        # Fetch all chronological updates
        cursor.execute(
            """
            SELECT update_number, update_text, event_type
            FROM incident_updates
            WHERE incident_id = %s
            ORDER BY update_number
            """,
            (incident_id,)
        )
        updates = [
            {"number": r[0], "text": r[1], "event_type": r[2]}
            for r in cursor.fetchall()
        ]
        
        # Fetch active tasks and their assigned teams
        cursor.execute(
            """
            SELECT t.id, t.task, t.priority, t.status, tm.name
            FROM tasks t
            LEFT JOIN teams tm ON tm.id = t.team_id
            WHERE t.incident_id = %s AND t.is_active = TRUE
            ORDER BY t.id
            """,
            (incident_id,)
        )
        
        tasks = []
        assignments = []
        for row in cursor.fetchall():
            task_id, task_text, priority, status, team_name = row
            tasks.append({
                "id": task_id,
                "task": task_text,
                "priority": priority,
                "status": status,
                "team_name": team_name
            })
            if team_name:
                assignments.append({
                    "task": task_text,
                    "team_name": team_name
                })
        
        return {
            "original_description": original_description,
            "original_severity": original_severity,
            "updates": updates,
            "previous_tasks": tasks,
            "previous_assignments": assignments
        }
        
    finally:
        cursor.close()
        connection.close()


def update_incident_status(incident_id, status):
    """Update incident status (active, stabilizing, or closed)."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        # Record closed_at timestamp when closing
        if status == "closed":
            cursor.execute(
                """
                UPDATE incidents
                SET status = %s, closed_at = NOW()
                WHERE id = %s
                """,
                (status, incident_id)
            )
        else:
            cursor.execute(
                "UPDATE incidents SET status = %s WHERE id = %s",
                (status, incident_id)
            )
        
        connection.commit()
        
    finally:
        cursor.close()
        connection.close()


def save_tasks(incident_id, tasks_list):
    """Insert tasks for an incident and return their IDs."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        task_ids = []
        
        for task in tasks_list:
            cursor.execute(
                """
                INSERT INTO tasks (incident_id, task, priority, is_active)
                VALUES (%s, %s, %s, TRUE)
                RETURNING id
                """,
                (incident_id, task.get("task"), task.get("priority"))
            )
            task_ids.append(cursor.fetchone()[0])
        
        connection.commit()
        return task_ids
        
    finally:
        cursor.close()
        connection.close()


def get_active_tasks(incident_id):
    """Return all active tasks for an incident."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            """
            SELECT t.id, t.task, t.priority, t.status, t.team_id, tm.name
            FROM tasks t
            LEFT JOIN teams tm ON tm.id = t.team_id
            WHERE t.incident_id = %s AND t.is_active = TRUE
            ORDER BY t.id
            """,
            (incident_id,)
        )
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                "id": row[0],
                "task": row[1],
                "priority": row[2],
                "status": row[3],
                "team_id": row[4],
                "team_name": row[5]
            })
        
        return tasks
        
    finally:
        cursor.close()
        connection.close()


def set_task_status(task_id, status):
    """Update a task's status."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        if status == "completed":
            cursor.execute(
                """
                UPDATE tasks
                SET status = %s, completed_at = NOW()
                WHERE id = %s
                """,
                (status, task_id)
            )
        else:
            cursor.execute(
                "UPDATE tasks SET status = %s WHERE id = %s",
                (status, task_id)
            )
        
        connection.commit()
        
    finally:
        cursor.close()
        connection.close()


def complete_task(task_id):
    """Mark task completed and free its assigned team."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        # Release the assigned team back to available
        cursor.execute("SELECT team_id FROM tasks WHERE id = %s", (task_id,))
        row = cursor.fetchone()
        
        if row and row[0]:
            cursor.execute(
                "UPDATE teams SET status = 'available' WHERE id = %s",
                (row[0],)
            )
        
        cursor.execute(
            """
            UPDATE tasks
            SET status = 'completed', completed_at = NOW()
            WHERE id = %s
            """,
            (task_id,)
        )
        
        connection.commit()
        
    finally:
        cursor.close()
        connection.close()


def complete_all_tasks(incident_id):
    """Complete all active tasks and free all teams for an incident."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        # Free all teams assigned to this incident's tasks
        cursor.execute(
            """
            SELECT team_id FROM tasks
            WHERE incident_id = %s AND is_active = TRUE AND team_id IS NOT NULL
            """,
            (incident_id,)
        )
        
        for row in cursor.fetchall():
            cursor.execute(
                "UPDATE teams SET status = 'available' WHERE id = %s",
                (row[0],)
            )
        
        # Mark every active task as completed
        cursor.execute(
            """
            UPDATE tasks
            SET status = 'completed', completed_at = NOW()
            WHERE incident_id = %s AND is_active = TRUE
            """,
            (incident_id,)
        )
        
        connection.commit()
        
    finally:
        cursor.close()
        connection.close()


def assign_team_to_task(task_id, team_id):
    """Link a team to a task and mark team as deployed."""
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        # Link team to task and mark both as assigned/deployed
        cursor.execute(
            """
            UPDATE tasks
            SET team_id = %s, status = 'assigned'
            WHERE id = %s
            """,
            (team_id, task_id)
        )
        
        cursor.execute(
            "UPDATE teams SET status = 'deployed' WHERE id = %s",
            (team_id,)
        )
        
        connection.commit()
        
    finally:
        cursor.close()
        connection.close()
