from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta


class ProjectProject(models.Model):
    _inherit = "project.project"

    # --------------------------------------------------
    # FIELDS
    # --------------------------------------------------
    use_sprint_management = fields.Boolean(
        string="Use Sprint Management",
        default=False,
        help="Enable sprint, backlog and epic features for this project",
    )

    sprint_ids = fields.One2many(
        "project.sprint",
        "project_id",
        string="Sprints",
    )

    epic_ids = fields.One2many(
        "project.epic",
        "project_id",
        string="Epics",
    )

    sprint_count = fields.Integer(
        string="Sprint Count",
        compute="_compute_sprint_count",
    )

    epic_count = fields.Integer(
        string="Epic Count",
        compute="_compute_epic_count",
    )

    backlog_task_count = fields.Integer(
        string="Backlog Tasks",
        compute="_compute_backlog_task_count",
        store=True,
    )

    active_sprint_id = fields.Many2one(
        "project.sprint",
        string="Active Sprint",
        compute="_compute_active_sprint",
        store=False,
    )

    # --------------------------------------------------
    # COMPUTES
    # --------------------------------------------------
    def _compute_sprint_count(self):
        for project in self:
            project.sprint_count = len(project.sprint_ids)

    def _compute_epic_count(self):
        for project in self:
            project.epic_count = len(project.epic_ids)

    @api.depends("task_ids", "task_ids.sprint_id", "use_sprint_management")
    def _compute_backlog_task_count(self):
        for project in self:
            if project.use_sprint_management:
                project.backlog_task_count = len(
                    project.task_ids.filtered(lambda t: not t.sprint_id)
                )
            else:
                project.backlog_task_count = 0

    def _compute_active_sprint(self):
        for project in self:
            project.active_sprint_id = self.env["project.sprint"].search(
                [
                    ("project_id", "=", project.id),
                    ("state", "=", "active"),
                ],
                limit=1,
            )

    # --------------------------------------------------
    # ORM OVERRIDES
    # --------------------------------------------------
    @api.model
    def create(self, vals):
        project = super().create(vals)

        # If flag is TRUE during project creation
        if project.use_sprint_management:
            project._ensure_sprint_stages()

        return project

    def write(self, vals):
        res = super().write(vals)

        # If flag is set to TRUE later
        if vals.get("use_sprint_management"):
            self._ensure_sprint_stages()

        return res

    # --------------------------------------------------
    # INTERNAL METHODS
    # --------------------------------------------------
    def _ensure_sprint_stages(self):
        """
        Create default kanban stages for sprint board
        (only once per project)
        """
        TaskType = self.env["project.task.type"]

        for project in self:
            if not project.use_sprint_management:
                continue

            # Do not recreate if at least one stage is already linked to the project
            existing_stage = TaskType.search(
                [("project_ids", "in", project.id)],
                limit=1,
            )
            if existing_stage:
                continue

            stages = [
                {"name": "To Do", "sequence": 10, "fold": False},
                {"name": "In Progress", "sequence": 20, "fold": False},
                {"name": "Blocked", "sequence": 30, "fold": False},
                {"name": "Done", "sequence": 40, "fold": True},
            ]

            for stage in stages:
                TaskType.create({
                    "name": stage["name"],
                    "sequence": stage["sequence"],
                    "fold": stage["fold"],
                    "project_ids": [(6, 0, [project.id])],
                    "use_in_sprint_board": True,
                })

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------
    def action_start_sprint_wizard(self):
        """Open wizard to start a new sprint"""
        self.ensure_one()

        if not self.use_sprint_management:
            raise UserError(_("Sprint management is not enabled for this project."))

        return {
            "name": _("Start Sprint"),
            "type": "ir.actions.act_window",
            "res_model": "project.sprint.start.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_project_id": self.id,
            },
        }

    def action_create_planned_sprint(self):
        """Open wizard to create a 'Waiting' sprint (Jira-style)"""
        self.ensure_one()
        return {
            "name": _("Create Sprint"),
            "type": "ir.actions.act_window",
            "res_model": "project.sprint.create.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_project_id": self.id,
            },
        }

    def action_open_active_sprint_board(self):
        """
        Project → Sprint Board button
        - Active sprint yoksa wizard açar
        - Varsa direkt sprint board açar
        """
        self.ensure_one()

        if not self.active_sprint_id:
            # No active sprint, open start sprint wizard
            return self.action_start_sprint_wizard()

        action = self.active_sprint_id.action_view_sprint_tasks()
        # Add buttons to action
        action['context'].update({
            'show_start_button': not self.active_sprint_id,
            'show_close_button': self.active_sprint_id and self.active_sprint_id.state == 'active',
        })
        return action

    def action_view_backlog(self):
        self.ensure_one()
        return {
            "name": _("Planning - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "project.task",
            "view_mode": "tree,form,kanban",
            "views": [
                (
                    self.env.ref(
                        "master_sprint_management.project_task_view_tree_backlog"
                    ).id,
                    "tree",
                ),
                (False, "form"),
                (False, "kanban"),
            ],
            "search_view_id": self.env.ref(
                "master_sprint_management.view_task_search_form"
            ).id,
            "domain": [
                ("project_id", "=", self.id),
                "|",
                ("sprint_id.state", "!=", "closed"),
                ("sprint_id", "=", False),
            ],
            "context": {
                "default_project_id": self.id,
                "group_by": "sprint_id",
                "create": True,
            },
        }

    def action_view_sprints(self):
        self.ensure_one()
        return {
            "name": _("Sprints - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "project.sprint",
            "view_mode": "tree,form",
            "domain": [("project_id", "=", self.id)],
            "context": {
                "default_project_id": self.id,
            },
        }

    def action_view_epics(self):
        self.ensure_one()
        return {
            "name": _("Epics - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "project.epic",
            "view_mode": "tree,form",
            "domain": [("project_id", "=", self.id)],
            "context": {
                "default_project_id": self.id,
            },
        }
