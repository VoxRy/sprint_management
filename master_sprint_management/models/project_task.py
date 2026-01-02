from odoo import fields, models


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


    # ✅ HELPER FIELD (attrs için şart)
    use_sprint_management = fields.Boolean(
        related="project_id.use_sprint_management",
        store=False,
        readonly=True,
    )
