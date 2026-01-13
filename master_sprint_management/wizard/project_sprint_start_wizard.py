# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta


class ProjectSprintStartWizard(models.TransientModel):
    _name = "project.sprint.start.wizard"
    _description = "Start Sprint Wizard"

    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        readonly=True,
    )
    sprint_id = fields.Many2one(
        "project.sprint",
        string="Existing Sprint",
        domain="[('project_id', '=', project_id), ('state', '=', 'waiting')]",
    )
    name = fields.Char(
        string="Sprint name",
        required=True,
    )
    duration = fields.Selection(
        [
            ("1", "1 week"),
            ("2", "2 weeks"),
            ("4", "4 weeks"),
            ("custom", "Custom"),
        ],
        string="Duration",
        default="2",
        required=True,
    )
    start_date = fields.Datetime(
        string="Start Date",
        required=True,
        default=fields.Datetime.now,
    )
    end_date = fields.Datetime(
        string="End Date",
        required=True,
        compute="_compute_end_date",
        store=True,
        readonly=False,
    )
    goal = fields.Text(string="Sprint Goal")
    task_ids = fields.Many2many("project.task", string="Tasks")
    task_count = fields.Integer(string="Task Count", compute="_compute_task_count")

    @api.depends("start_date", "duration")
    def _compute_end_date(self):
        for wizard in self:
            if wizard.start_date and wizard.duration != "custom":
                weeks = int(wizard.duration)
                wizard.end_date = wizard.start_date + timedelta(weeks=weeks)
            elif not wizard.end_date:
                wizard.end_date = wizard.start_date

    @api.depends("task_ids")
    def _compute_task_count(self):
        for wizard in self:
            wizard.task_count = len(wizard.task_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "project_id" in fields_list and self.env.context.get("default_project_id"):
            res["project_id"] = self.env.context["default_project_id"]
        if "start_date" in fields_list:
            res["start_date"] = fields.Datetime.now()
        if "sprint_id" in fields_list and self.env.context.get("active_id") and self.env.context.get("active_model") == "project.sprint":
            res["sprint_id"] = self.env.context["active_id"]
        if "name" in fields_list:
            if res.get("sprint_id"):
                res["name"] = self.env["project.sprint"].browse(res["sprint_id"]).name
            else:
                res["name"] = self._generate_sprint_name(res.get("start_date") or fields.Datetime.now())
        if "task_ids" in fields_list:
            if self.env.context.get("active_model") == "project.task" and self.env.context.get("active_ids"):
                res["task_ids"] = [(6, 0, self.env.context["active_ids"])]
            elif res.get("sprint_id"):
                # If starting an existing sprint, show its currents tasks
                sprint = self.env["project.sprint"].browse(res["sprint_id"])
                res["task_ids"] = [(6, 0, sprint.task_ids.ids)]
        return res

    def _generate_sprint_name(self, start_date):
        """Generate sprint name as 'Month Year' (e.g., 'Ocak 26')"""
        if not start_date:
            return ""
        month_names = {
            1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
            5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
            9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
        }
        month = month_names.get(start_date.month, "")
        year = str(start_date.year)[2:]  # Last two digits for '26'
        return f"{month} {year}"

    @api.onchange("start_date")
    def _onchange_start_date(self):
        if self.start_date:
            self.name = self._generate_sprint_name(self.start_date)

    def action_start_sprint(self):
        self.ensure_one()

        # Check if there's already an active sprint
        active_sprint = self.env["project.sprint"].search(
            [
                ("project_id", "=", self.project_id.id),
                ("state", "=", "active"),
            ],
            limit=1,
        )
        if active_sprint:
            raise UserError(
                _(
                    'There is already an active sprint "%s" in this project. '
                    "Please close it before starting a new one."
                )
                % active_sprint.name
            )

        # Use end_date from wizard
        end_date = self.end_date

        # Ensure sprint stages exist
        if self.project_id.use_sprint_management:
            self.project_id._ensure_sprint_stages()

        if self.sprint_id:
            # Update existing planned sprint
            sprint = self.sprint_id
            sprint.write({
                "name": self.name,
                "start_date": self.start_date,
                "end_date": end_date,
                "goal": self.goal,
                "state": "active",
            })
        else:
            # Create and activate new sprint
            sprint = self.env["project.sprint"].create({
                "name": self.name,
                "project_id": self.project_id.id,
                "start_date": self.start_date,
                "end_date": end_date,
                "goal": self.goal,
                "state": "active",
            })

        sprint_name = sprint.name

        # Move selected tasks to the new sprint
        if self.task_ids:
            self.task_ids.write({"sprint_id": sprint.id})

        sprint.message_post(
            body=_("<p>Sprint <strong>%s</strong> has been started with %d tasks.</p>") % (sprint.name, len(self.task_ids))
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sprint Started"),
                "message": _('Sprint "%s" has been created and activated!') % sprint.name,
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": "project.sprint",
                    "view_mode": "form",
                    "res_id": sprint.id,
                    "views": [(False, "form")],
                    "target": "current",
                },
            },
        }

