from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectTaskMoveSprint(models.TransientModel):
    _name = "project.task.move.sprint"
    _description = "Move Tasks to Sprint"

    task_ids = fields.Many2many("project.task", string="Tasks", required=True)
    project_id = fields.Many2one("project.project", string="Project", required=True)
    sprint_id = fields.Many2one(
        "project.sprint",
        string="Target Sprint",
        domain="[('project_id', '=', project_id), ('state', 'in', ['waiting','active'])]",
        required=True,
    )

    task_count = fields.Integer(string="Number of Tasks", compute="_compute_task_count")

    @api.depends("task_ids")
    def _compute_task_count(self):
        for wizard in self:
            wizard.task_count = len(wizard.task_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            tasks = self.env["project.task"].browse(active_ids)
            res["task_ids"] = [(6, 0, active_ids)]
            if tasks:
                res["project_id"] = tasks[0].project_id.id

                projects = tasks.mapped("project_id")
                if len(projects) > 1:
                    raise UserError(
                        _(
                            "All selected tasks must be from the same project.\n"
                            "You have selected tasks from: %s"
                        )
                        % ", ".join(projects.mapped("name"))
                    )
        return res

    def action_move_tasks(self):
        self.ensure_one()

        if not self.task_ids:
            raise UserError(_("No tasks selected!"))

        self.task_ids.write({"sprint_id": self.sprint_id.id})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _('%d task(s) moved to sprint "%s"') % (
                    len(self.task_ids),
                    self.sprint_id.name,
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
