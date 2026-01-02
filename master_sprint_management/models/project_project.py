from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
    # AUTO CREATE SPRINT STAGES
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

            # Eğer projeye bağlı en az 1 stage varsa tekrar oluşturma
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
    # ORM OVERRIDES
    # --------------------------------------------------
    @api.model
    def create(self, vals):
        project = super().create(vals)

        # Project create edilirken flag TRUE ise
        if project.use_sprint_management:
            project._ensure_sprint_stages()

        return project

    def write(self, vals):
        res = super().write(vals)

        # Flag sonradan TRUE yapılırsa
        if vals.get("use_sprint_management"):
            self._ensure_sprint_stages()

        return res

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------
    def action_open_active_sprint_board(self):
        """
        Project → Sprint Board button
        - Active sprint yoksa hata verir
        - Varsa direkt sprint board açar
        """
        self.ensure_one()

        if not self.active_sprint_id:
            raise UserError(
                _("There is no active sprint in this project.\n"
                  "Please activate a sprint first.")
            )

        return self.active_sprint_id.action_view_sprint_tasks()

    def action_view_backlog(self):
        self.ensure_one()
        return {
            "name": _("Backlog - %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "project.task",
            "view_mode": "tree,form",
            "domain": [
                ("project_id", "=", self.id),
                ("sprint_id", "=", False),
            ],
            "context": {
                "default_project_id": self.id,
                "search_default_filter_backlog": 1,
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
