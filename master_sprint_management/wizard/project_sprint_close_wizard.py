# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProjectSprintCloseWizard(models.TransientModel):
    _name = "project.sprint.close.wizard"
    _description = "Sprint Close Wizard"

    sprint_id = fields.Many2one(
        "project.sprint",
        string="Sprint",
        required=True,
    )
    project_id = fields.Many2one(
        "project.project",
        related="sprint_id.project_id",
        store=True,
        readonly=True,
    )
    next_sprint_id = fields.Many2one(
        "project.sprint",
        string="Move Tasks To",
    )
    incomplete_task_count = fields.Integer(
        string="Incomplete Tasks",
    )

    action_type = fields.Selection(
        [
            ("move", "Move to Next Sprint"),
            ("backlog", "Move to Backlog"),
        ],
        string="Action for Incomplete Tasks",
        default="move",
        required=True,
    )

    incomplete_task_ids = fields.Many2many(
        "project.task",
        string="Incomplete Tasks",
        compute="_compute_incomplete_tasks",
    )

    @api.depends("sprint_id")
    def _compute_incomplete_tasks(self):
        for wizard in self:
            if wizard.sprint_id:
                wizard.incomplete_task_ids = wizard.sprint_id.task_ids.filtered(
                    lambda t: not (t.stage_id and (t.stage_id.is_closed or t.stage_id.fold))
                )
            else:
                wizard.incomplete_task_ids = False

    @api.onchange("action_type")
    def _onchange_action_type(self):
        if self.action_type != "move":
            self.next_sprint_id = False

    def action_close_sprint(self):
        self.ensure_one()

        sprint = self.sprint_id

        # Snapshot before moving tasks
        snapshot_vals = sprint._compute_snapshot_values()
        sprint.write(snapshot_vals)

        incomplete_tasks = sprint.task_ids.filtered(
            lambda t: not (t.stage_id and (t.stage_id.is_closed or t.stage_id.fold))
        )

        if incomplete_tasks and self.action_type == "move":
            if not self.next_sprint_id:
                raise UserError(_("Please select a target sprint!"))

            for task in incomplete_tasks:
                task.message_post(
                    body=_(
                        "<p>Task moved from sprint <strong>%s</strong> "
                        "to sprint <strong>%s</strong></p>"
                        "<p>Reason: Sprint closed with incomplete work.</p>"
                        "<p><em>Original sprint statistics were preserved.</em></p>"
                    )
                    % (sprint.name, self.next_sprint_id.name)
                )

            incomplete_tasks.write(
                {
                    "previous_sprint_id": sprint.id,
                    "sprint_id": self.next_sprint_id.id,
                }
            )

            message = _('%d incomplete task(s) moved to sprint "%s"') % (
                len(incomplete_tasks),
                self.next_sprint_id.name,
            )

        elif incomplete_tasks and self.action_type == "backlog":
            for task in incomplete_tasks:
                task.message_post(
                    body=_(
                        "<p>Task moved from sprint <strong>%s</strong> "
                        "to <strong>Backlog</strong></p>"
                        "<p>Reason: Sprint closed with incomplete work.</p>"
                    )
                    % sprint.name
                )

            incomplete_tasks.write({"sprint_id": False})
            message = _("%d incomplete task(s) moved to backlog") % len(incomplete_tasks)

        else:
            message = _("Sprint closed successfully. All tasks were completed!")

        sprint.write({"state": "closed"})

        sprint.message_post(
            body=_(
                "<p><strong>Sprint Closed Summary:</strong></p>"
                "<ul>"
                "<li>Total Tasks (Snapshot): %d</li>"
                "<li>Done (Snapshot): %d</li>"
                "<li>Incomplete at close: %d</li>"
                "<li>Action Taken: %s</li>"
                "</ul>"
            )
            % (
                sprint.snapshot_task_count,
                sprint.snapshot_done_count,
                len(incomplete_tasks),
                dict(self._fields["action_type"].selection).get(self.action_type),
            )
        )

        # ✅ Close the popup after showing notification
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sprint Closed"),
                "message": message,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
