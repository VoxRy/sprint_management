from odoo import api, fields, models


class ProjectEpic(models.Model):
    _name = "project.epic"
    _description = "Project Epic"
    _order = "sequence, name"

    name = fields.Char(string="Epic Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)

    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        ondelete="cascade",
        domain=[("use_sprint_management", "=", True)],
    )

    description = fields.Html(string="Description")
    color = fields.Integer(string="Color", default=0)

    task_ids = fields.One2many("project.task", "epic_id", string="Tasks")
    task_count = fields.Integer(string="Tasks", compute="_compute_task_count", store=True)

    display_completion_percentage = fields.Float(
        string="Completion %",
        compute="_compute_display_completion",
    )

    @api.depends("task_ids", "task_ids.stage_id", "task_ids.stage_id.fold")
    def _compute_display_completion(self):
        for epic in self:
            if not epic.task_count:
                epic.display_completion_percentage = 0.0
                continue
            
            done_tasks = epic.task_ids.filtered(
                lambda t: t.stage_id and (t.stage_id.is_closed or t.stage_id.fold)
            )
            epic.display_completion_percentage = round(
                (len(done_tasks) / epic.task_count) * 100, 2
            )

    @api.depends("task_ids")
    def _compute_task_count(self):
        for epic in self:
            epic.task_count = len(epic.task_ids)

    def action_view_epic_tasks(self):
        self.ensure_one()
        return {
            "name": self.name,
            "type": "ir.actions.act_window",
            "res_model": "project.task",
            "view_mode": "kanban,tree,form",
            "domain": [("epic_id", "=", self.id)],
            "context": {
                "default_epic_id": self.id,
                "default_project_id": self.project_id.id,
            },
        }
