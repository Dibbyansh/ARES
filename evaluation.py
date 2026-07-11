# Quality evaluation — validates agent outputs with rules and optional AI review
from tools.llm import ask_ai
from utils.json_parser import parse_json


def check_classification(state):
    """Validate classification fields. Returns passed flag and issues list."""
    
    issues = []
    
    if not state.get("category"):
        issues.append("Missing category")
    
    severity = state.get("severity", "").lower()
    valid_severities = ["low", "medium", "high", "critical"]
    if severity not in valid_severities:
        issues.append(f"Invalid severity: {severity}")
    
    if not state.get("location"):
        issues.append("Missing location")
    
    # Serious incidents should have identified risks
    risks = state.get("risks", [])
    if severity in ["medium", "high", "critical"] and len(risks) == 0:
        issues.append("No risks identified for serious incident")
    
    if not state.get("incident_id"):
        issues.append("Missing incident ID")
    
    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def check_tasks(state):
    """Validate task list structure and severity-appropriate count."""
    
    issues = []
    tasks = state.get("tasks", [])
    severity = state.get("severity", "").lower()
    
    if len(tasks) == 0:
        issues.append("No tasks generated")
        return {"passed": False, "issues": issues}
    
    # Validate each task has description and valid priority
    for i, task in enumerate(tasks):
        if not task.get("task"):
            issues.append(f"Task {i} missing description")
        
        priority = task.get("priority", "").lower()
        if priority not in ["low", "medium", "high"]:
            issues.append(f"Task {i} has invalid priority: {priority}")
    
    # Expect more tasks for higher severity incidents
    if severity == "critical" and len(tasks) < 4:
        issues.append("Critical incident should have at least 4 tasks")
    elif severity == "high" and len(tasks) < 3:
        issues.append("High severity incident should have at least 3 tasks")
    
    if severity in ["high", "critical"]:
        high_priority_count = sum(1 for t in tasks if t.get("priority") == "high")
        if high_priority_count == 0:
            issues.append("Serious incident should have high-priority tasks")
    
    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def check_assignments(state):
    """Validate team assignments. Returns passed flag and issues list."""
    
    issues = []
    tasks = state.get("tasks", [])
    assignments = state.get("assignments", [])
    
    if len(tasks) > 0 and len(assignments) == 0:
        issues.append("Tasks exist but no teams assigned")
    
    for i, assignment in enumerate(assignments):
        if not assignment.get("team_name"):
            issues.append(f"Assignment {i} missing team name")
        if not assignment.get("task"):
            issues.append(f"Assignment {i} missing task")
    
    # Each team should only be assigned once
    team_names = [a.get("team_name") for a in assignments]
    if len(team_names) != len(set(team_names)):
        issues.append("Same team assigned to multiple tasks")
    
    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def ai_review_tasks(state):
    """AI review of task plan for high/critical incidents."""
    
    # AI review only runs for high/critical severity
    severity = state.get("severity", "").lower()
    if severity not in ["high", "critical"]:
        return {"passed": True, "issues": [], "missing_tasks": []}
    
    incident = state.get("incident", "")
    category = state.get("category", "")
    risks = state.get("risks", [])
    tasks = state.get("tasks", [])
    
    tasks_text = "\n".join(
        f"- [{t.get('priority', '?').upper()}] {t.get('task')}"
        for t in tasks
    )
    
    risks_text = ", ".join(risks) if risks else "none"
    
    prompt = f"""You are a quality reviewer for emergency response planning.

Incident: {incident}
Category: {category}
Severity: {severity}
Risks: {risks_text}

Proposed Tasks:
{tasks_text}

Review Questions:
1. Are all critical risks addressed?
2. Are priorities appropriate?
3. Are any critical tasks missing?
4. Is the response proportional to severity?

If tasks are GOOD, return:
{{"quality": "good", "missing_tasks": []}}

If tasks have ISSUES, return:
{{"quality": "needs_improvement", "missing_tasks": ["task1", "task2"]}}

Return ONLY JSON:"""
    
    response = ask_ai(prompt)
    review = parse_json(response)
    
    if not review:
        return {"passed": True, "issues": [], "missing_tasks": []}
    
    quality = review.get("quality", "good")
    missing_tasks = review.get("missing_tasks", [])
    
    if quality == "good":
        return {"passed": True, "issues": [], "missing_tasks": []}
    else:
        return {
            "passed": False,
            "issues": ["AI review found missing critical tasks"],
            "missing_tasks": missing_tasks
        }


def evaluate_agent_output(state, agent_name):
    """Dispatch quality checks to the appropriate agent evaluator."""
    
    # Dispatch to the appropriate evaluator by agent name
    if agent_name == "classifier":
        return evaluate_classifier(state)
    elif agent_name == "planner":
        return evaluate_planner(state)
    elif agent_name == "assigner":
        return evaluate_assigner(state)
    else:
        return {"passed": True}


def evaluate_classifier(state):
    """Run classification quality checks."""
    
    print("   🔍 Evaluating classification...")
    
    result = check_classification(state)
    
    if not result["passed"]:
        return {
            "passed": False,
            "action": "retry",
            "reason": "Classification incomplete: " + ", ".join(result["issues"]),
            "feedback": "Please provide: " + ", ".join(result["issues"])
        }
    
    print("   ✓ Classification looks good")
    return {"passed": True}


def evaluate_planner(state):
    """Run task plan quality checks with optional AI review."""
    
    print("   🔍 Evaluating task plan...")
    
    # Tier 1: fast rule-based checks
    result = check_tasks(state)
    
    if not result["passed"]:
        return {
            "passed": False,
            "action": "retry",
            "reason": "Task plan has issues: " + ", ".join(result["issues"]),
            "feedback": "Fix these issues: " + ", ".join(result["issues"])
        }
    
    # Tier 2: AI review for high/critical incidents only
    severity = state.get("severity", "").lower()
    if severity in ["high", "critical"]:
        print("   🤖 Running AI quality review...")
        ai_result = ai_review_tasks(state)
        
        if not ai_result["passed"]:
            return {
                "passed": False,
                "action": "replan",
                "reason": "Missing critical tasks",
                "feedback": "Add these critical tasks",
                "missing_tasks": ai_result["missing_tasks"]
            }
    
    print("   ✓ Task plan looks good")
    return {"passed": True}


def evaluate_assigner(state):
    """Run assignment quality checks."""
    
    print("   🔍 Evaluating team assignments...")
    
    result = check_assignments(state)
    
    if not result["passed"]:
        return {
            "passed": False,
            "action": "retry",
            "reason": "Assignment issues: " + ", ".join(result["issues"]),
            "feedback": "Fix these issues: " + ", ".join(result["issues"])
        }
    
    print("   ✓ Assignments look good")
    return {"passed": True}
