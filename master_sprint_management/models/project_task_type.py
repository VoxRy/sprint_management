from odoo import fields, models


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    use_in_sprint_board = fields.Boolean(
        string="Use in Sprint Board",
        default=True,
        help="If enabled, this stage will appear in Sprint Board kanban"
    )
