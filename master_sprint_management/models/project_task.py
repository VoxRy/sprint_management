from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    sprint_id = fields.Many2one(
        "project.sprint",
        string="Sprint",
        ondelete="set null",
        domain="[('project_id', '=', project_id), ('state', 'in', ['waiting','active'])]",
    )

    epic_id = fields.Many2one(
        "project.epic",
        string="Epic",
        ondelete="set null",
        domain="[('project_id', '=', project_id)]",
    )

    previous_sprint_id = fields.Many2one(
        "project.sprint",
        string="Previous Sprint",
        readonly=True,
        help="Sprint this task was moved from",
    )

    # BANNER HELPERS (Non-stored related for UI)
    sprint_goal = fields.Text(related="sprint_id.goal", string="Sprint Goal")
    sprint_start_date = fields.Datetime(related="sprint_id.start_date")
    sprint_end_date = fields.Datetime(related="sprint_id.end_date")

    # HELPER FIELD (Required for attrs)
    use_sprint_management = fields.Boolean(
        related="project_id.use_sprint_management",
        store=False,
        readonly=True,
    )

    # --------------------------------------------------
    # ACTIONS FOR SPRINT BOARD
    # --------------------------------------------------
    def action_start_sprint_from_board(self):
        """Start sprint wizard from sprint board"""
        project_id = self.env.context.get("default_project_id") or (self.project_id.id if self else False)
        if not project_id:
            return False
        
        project = self.env["project.project"].browse(project_id)
        return project.action_start_sprint_wizard()

    def action_close_sprint_from_board(self):
        """Close active sprint from sprint board"""
        project_id = self.env.context.get("default_project_id") or (self.project_id.id if self else False)
        if not project_id:
            return False
        
        project = self.env["project.project"].browse(project_id)
        if project.active_sprint_id:
            return project.active_sprint_id.action_close_sprint()
        return False

    def action_view_planning_from_board(self):
        """Navigate back to Planning view from board"""
        project_id = self.env.context.get("default_project_id") or (self.project_id.id if self else False)
        if not project_id:
            return False
        project = self.env["project.project"].browse(project_id)
        return project.action_view_backlog()
