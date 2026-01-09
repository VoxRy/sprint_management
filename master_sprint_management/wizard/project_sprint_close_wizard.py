from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class ProjectSprintCloseWizard(models.TransientModel):
    _name = "project.sprint.close.wizard"
    _description = "Sprint Close Wizard"

    sprint_id = fields.Many2one(
        "project.sprint",
        string="Sprint",
        required=True,
        readonly=True,
    )
    project_id = fields.Many2one(
        "project.project",
        related="sprint_id.project_id",
        store=True,
        readonly=True,
    )
    close_date = fields.Datetime(
        string="Close Date",
        required=True,
        default=fields.Datetime.now,
        help="Date when the sprint will be closed",
    )
    completed_task_count = fields.Integer(
        string="Completed Tasks",
        compute="_compute_task_counts",
    )
    incomplete_task_count = fields.Integer(
        string="Incomplete Tasks",
        compute="_compute_task_counts",
    )
    action_type = fields.Selection(
        [
            ("new", "New sprint"),
            ("existing", "Existing sprint"),
            ("backlog", "Backlog"),
        ],
        string="Move open issues to",
        default="new",
        required=True,
    )
    next_sprint_id = fields.Many2one(
        "project.sprint",
        string="Select Sprint",
        domain="[('project_id', '=', project_id), ('state', 'in', ['waiting','active']), ('id', '!=', sprint_id)]",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "sprint_id" in fields_list and self.env.context.get("default_sprint_id"):
            res["sprint_id"] = self.env.context["default_sprint_id"]
        if "close_date" in fields_list:
            res["close_date"] = fields.Datetime.now()
        
        # Auto-suggest next sprint
        if "sprint_id" in res and res["sprint_id"]:
            sprint = self.env["project.sprint"].browse(res["sprint_id"])
            next_sprint = self.env["project.sprint"].search(
                [
                    ("project_id", "=", sprint.project_id.id),
                    ("state", "in", ["waiting", "active"]),
                    ("id", "!=", sprint.id),
                    ("start_date", ">=", fields.Datetime.now()),
                ],
                order="start_date",
                limit=1,
            )
            if next_sprint and "next_sprint_id" in fields_list:
                res["next_sprint_id"] = next_sprint.id
        return res

    @api.depends("sprint_id")
    def _compute_task_counts(self):
        for wizard in self:
            if wizard.sprint_id:
                completed = wizard.sprint_id.task_ids.filtered(
                    lambda t: t.stage_id and (t.stage_id.is_closed or t.stage_id.fold)
                )
                wizard.completed_task_count = len(completed)
                wizard.incomplete_task_count = len(wizard.sprint_id.task_ids) - len(completed)
            else:
                wizard.completed_task_count = 0
                wizard.incomplete_task_count = 0

    @api.onchange("action_type")
    def _onchange_action_type(self):
        if self.action_type != "existing":
            self.next_sprint_id = False

    def action_close_sprint(self):
        self.ensure_one()

        sprint = self.sprint_id

        # Update end_date if close_date is different
        if self.close_date != sprint.end_date:
            sprint.write({"end_date": self.close_date})

        # Snapshot before moving tasks
        snapshot_vals = sprint._compute_snapshot_values()
        sprint.write(snapshot_vals)

        incomplete_tasks = sprint.task_ids.filtered(
            lambda t: not (t.stage_id and (t.stage_id.is_closed or t.stage_id.fold))
        )

        if incomplete_tasks:
            target_sprint = False
            
            if self.action_type == "new":
                # Auto-create next month's sprint
                start_date = self.close_date
                month_names = {
                    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
                    5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
                    9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
                }
                # Calculate next month
                next_month = start_date.month + 1
                next_year = start_date.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                
                month = month_names.get(next_month, "")
                year = str(next_year)[2:]
                new_sprint_name = f"{month} {year}"
                
                target_sprint = self.env["project.sprint"].create({
                    "name": new_sprint_name,
                    "project_id": self.project_id.id,
                    "start_date": start_date,
                    "end_date": start_date + timedelta(weeks=4), # Default 4 weeks for monthly
                    "state": "waiting",
                })
            
            elif self.action_type == "existing":
                if not self.next_sprint_id:
                    raise UserError(_("Please select a target sprint for incomplete tasks!"))
                target_sprint = self.next_sprint_id
            
            if target_sprint:
                for task in incomplete_tasks:
                    task.message_post(
                        body=_(
                            "<p>Task moved from sprint <strong>%s</strong> "
                            "to sprint <strong>%s</strong></p>"
                            "<p>Reason: Sprint closed with incomplete work.</p>"
                        )
                        % (sprint.name, target_sprint.name)
                    )

                incomplete_tasks.write(
                    {
                        "previous_sprint_id": sprint.id,
                        "sprint_id": target_sprint.id,
                    }
                )
                message = _('%d incomplete task(s) moved to sprint "%s"') % (
                    len(incomplete_tasks),
                    target_sprint.name,
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
                "<li>Close Date: %s</li>"
                "</ul>"
            )
            % (
                sprint.snapshot_task_count,
                sprint.snapshot_done_count,
                len(incomplete_tasks),
                self.close_date,
            )
        )

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
