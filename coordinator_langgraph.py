# LangGraph coordinator — AI-driven router decides which agent runs next
from typing import TypedDict, Annotated, Literal
import operator
from langgraph.graph import StateGraph, END

from agents.classifier import classify_incident
from agents.planner import plan_tasks
from agents.assigner import assign_teams
from agents.tracker import activate_teams, stabilize_incident, close_incident
from agents.alerter import send_alert
from tools.llm import ask_ai
from utils.json_parser import parse_json


class IncidentState(TypedDict, total=False):
    """Shared workflow state passed between LangGraph nodes."""
    incident: str     
    event_type: str    
    category: str                         
    severity: str                         
    location: str                         
    risks: list                           
    incident_id: int                      
    tasks: list                           
    task_ids: list                        
    assignments: list                     
    next_action: str                      
    step_count: int                       
    history: Annotated[list, operator.add]  # Appends across nodes via operator.add


def classifier_node(state: IncidentState) -> IncidentState:
    """Run classifier agent and merge results into state."""
    print("🔍 Classifying incident...")

    incident_data = dict(state)
    
    updated_data = classify_incident(incident_data)
    
    # Merge classifier output back into graph state
    result = dict(state)
    result.update(updated_data)
    
    return result   


def planner_node(state: IncidentState) -> IncidentState:
    """Run planner agent and merge results into state."""
    print("📋 Planning response tasks...")
    
    incident_data = dict(state)
    updated_data = plan_tasks(incident_data)
    
    result = dict(state)
    result.update(updated_data)
    
    return result


def assigner_node(state: IncidentState) -> IncidentState:
    """Run assigner agent and merge results into state."""
    print("🧑‍🚒 Assigning teams...")
    
    incident_data = dict(state)
    updated_data = assign_teams(incident_data)
    
    result = dict(state)
    result.update(updated_data)
    
    return result


def tracker_activate_node(state: IncidentState) -> IncidentState:
    """Activate assigned teams."""
    print("📊 Activating teams...")
    
    incident_data = dict(state)
    activate_teams(incident_data)
    
    return state


def tracker_stabilize_node(state: IncidentState) -> IncidentState:
    """Complete urgent tasks for a stabilizing incident."""
    print("📊 Stabilizing incident...")
    
    incident_data = dict(state)
    stabilize_incident(incident_data)
    
    return state


def tracker_close_node(state: IncidentState) -> IncidentState:
    """Close incident and complete all remaining tasks."""
    print("📊 Closing incident...")
    
    incident_data = dict(state)
    close_incident(incident_data)
    
    return state


def alerter_node(state: IncidentState) -> IncidentState:
    """Send Telegram alert for the incident."""
    print("🚨 Sending alert...")
    
    incident_data = dict(state)
    send_alert(incident_data)
    
    return state


def router_node(state: IncidentState) -> IncidentState:
    """Ask AI which agent should run next based on current state."""
    
    # Safety cap to prevent infinite routing loops
    step_count = state.get("step_count", 0)
    if step_count >= 10:
        print("⚠️  Reached maximum steps (10)")
        result = dict(state)
        result["next_action"] = "done"
        return result
    
    # Summarize current state for the routing prompt
    summary_lines = [f"Input: {state.get('incident', '')}"]
    
    if state.get("category"):
        summary_lines.append(f"Category: {state.get('category')} | Severity: {state.get('severity')}")
    if state.get("location"):
        summary_lines.append(f"Location: {state.get('location')}")
    if state.get("incident_id"):
        summary_lines.append(f"Incident ID: {state.get('incident_id')}")
    if state.get("tasks"):
        summary_lines.append(f"Tasks: {len(state.get('tasks', []))} generated")
    if state.get("assignments"):
        summary_lines.append(f"Teams: {len(state.get('assignments', []))} assigned")
    
    summary = "\n".join(summary_lines)
    
    history = state.get("history", [])
    history_text = "\n".join(f"- {h}" for h in history) if history else "(nothing yet)"
    
    # Ask AI which agent to invoke next
    prompt = f"""You are an emergency response coordinator. Decide the next action.

Current State:
{summary}

Actions Completed:
{history_text}

Available Actions:
- classifier: Classify the incident (type, severity, location)
- planner: Generate response tasks
- assigner: Assign teams to tasks
- tracker_activate: Start teams working
- tracker_stabilize: Complete urgent tasks (situation improving)
- tracker_close: Close incident completely
- alerter: Send Telegram notification
- done: All actions complete

Rules:
1. Classify first if not done
2. Plan tasks after classification
3. Assign teams after planning
4. Activate teams after assignment
5. Alert for new incidents
6. Use tracker_close for resolve events
7. Return "done" when finished

Return ONLY this JSON:
{{"action": "classifier", "reason": "need to classify first"}}"""
    
    response = ask_ai(prompt)
    decision = parse_json(response)
    
    if not decision:
        result = dict(state)
        result["next_action"] = "done"
        return result
    
    action = decision.get("action", "done")
    reason = decision.get("reason", "")
    
    print(f"→ [{step_count + 1}] {action}: {reason}")
    
    # Record routing decision and increment step counter
    result = dict(state)
    result["next_action"] = action
    result["step_count"] = step_count + 1
    result["history"] = history + [f"{action} — {reason}"]
    
    return result


def route_to_next_node(state: IncidentState) -> Literal[
    "classifier", "planner", "assigner", 
    "tracker_activate", "tracker_stabilize", "tracker_close",
    "alerter", "__end__"
]:
    """Map router decision to the next graph node name."""
    
    action = state.get("next_action", "done")
    
    # Map AI action names to graph node names
    routes = {
        "classifier": "classifier",
        "planner": "planner",
        "assigner": "assigner",
        "tracker_activate": "tracker_activate",
        "tracker_stabilize": "tracker_stabilize",
        "tracker_close": "tracker_close",
        "alerter": "alerter",
        "done": "__end__",
    }
    
    next_node = routes.get(action, "__end__")  # type: ignore
    
    if next_node == "__end__":
        print("✓ Workflow complete!")
    
    return next_node


def create_workflow_graph():
    """Build and compile the LangGraph agent workflow."""
    
    print("🔧 Building LangGraph workflow...")
    
    workflow = StateGraph(IncidentState)
    
    # Register all agent nodes plus the AI router
    workflow.add_node("router", router_node)
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("assigner", assigner_node)
    workflow.add_node("tracker_activate", tracker_activate_node)
    workflow.add_node("tracker_stabilize", tracker_stabilize_node)
    workflow.add_node("tracker_close", tracker_close_node)
    workflow.add_node("alerter", alerter_node)
    
    # Router is the entry point — it decides the first agent
    workflow.set_entry_point("router")
    
    # Router conditionally branches to any agent or END
    workflow.add_conditional_edges(
        "router",                    # From router node
        route_to_next_node,          # Use this function to decide
        {                            # Map of possible destinations
            "classifier": "classifier",
            "planner": "planner",
            "assigner": "assigner",
            "tracker_activate": "tracker_activate",
            "tracker_stabilize": "tracker_stabilize",
            "tracker_close": "tracker_close",
            "alerter": "alerter",
            "__end__": END,          # Special: end the workflow
        }
    )
    
    # Every agent returns to the router for the next decision
    workflow.add_edge("classifier", "router")
    workflow.add_edge("planner", "router")
    workflow.add_edge("assigner", "router")
    workflow.add_edge("tracker_activate", "router")
    workflow.add_edge("tracker_stabilize", "router")
    workflow.add_edge("tracker_close", "router")
    workflow.add_edge("alerter", "router")
    
    print("✓ Workflow compiled!")
    return workflow.compile()


def handle_incident_with_langgraph(incident_text):
    """Process an incident via the LangGraph workflow."""
    print("⚡ Processing with LangGraph...")
    print("-" * 60)

    graph = create_workflow_graph()
    
    # Seed the graph with empty state — agents fill it in step by step
    initial_state: IncidentState = {
        "incident": incident_text,
        "event_type": "new",
        "category": "",
        "severity": "",
        "location": "",
        "risks": [],
        "incident_id": 0,
        "tasks": [],
        "task_ids": [],
        "assignments": [],
        "next_action": "",
        "step_count": 0,
        "history": [],
    }
    
    # Run the workflow until router returns "done"
    final_state = graph.invoke(initial_state)
    
    print_summary(final_state)
    
    return final_state


def print_summary(state):
    """Print final incident summary to console."""
    
    print("\n" + "=" * 60)
    print("INCIDENT SUMMARY")
    print("=" * 60)
    
    print(f"Incident ID: {state.get('incident_id')}")
    print(f"Type: {state.get('event_type')}")
    print(f"Category: {state.get('category')}")
    print(f"Severity: {state.get('severity')}")
    print(f"Location: {state.get('location')}")
    
    if state.get("tasks"):
        print(f"\nTasks ({len(state['tasks'])}):")
        for i, task in enumerate(state["tasks"], 1):
            priority = task.get("priority", "?").upper()
            print(f"  {i}. [{priority}] {task.get('task')}")
    
    if state.get("assignments"):
        print(f"\nTeam Assignments:")
        for assignment in state["assignments"]:
            print(f"  - {assignment['team_name']} → {assignment['task']}")
    
    status = "closed" if state.get("event_type") == "resolve" else "active"
    print(f"\nStatus: {status}")
    print("=" * 60)
