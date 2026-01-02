{
    "name": "Master Sprint Management",
    "version": "15.0.2.0.0",
    "category": "Project",
    "summary": "Agile Sprint Management for Odoo 15 Community (Stage-based board, no risky overrides)",
    "description": """
Master Sprint Management (Odoo 15 Community)
===========================================
- Project-level Sprint Management toggle
- Sprints (Waiting/Active/Closed) with snapshot reporting on close
- Epics linked to project/tasks
- Backlog list view + SearchPanel filters (Epic, Sprint, Tags, Stage)
- Sprint Board: stage-based kanban (no task_state override)
- Bulk move tasks to sprint (wizard)
""",
    "author": "Kais Akram",
    "website": "https://kaisakram.com",
    "depends": ["project", "mail"],
    "data": [
    "security/ir.model.access.csv",

    # =====================
    # CORE VIEWS (ÖNCE)
    # =====================
    "views/project_project_views.xml",
    "views/project_sprint_views.xml",
    "views/project_epic_views.xml",
    "views/project_task_type_views.xml",
    "views/project_task_views.xml",          # 👈 view_task_tree_backlog BURADA

    # =====================
    # WIZARDS
    # =====================
    "views/project_sprint_close_wizard_views.xml",
    "views/sprint_move_wizard_views.xml",

    # =====================
    # ACTIONS & MENUS (EN SON)
    # =====================
    "views/actions.xml",
    "views/menu_views.xml",
],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
