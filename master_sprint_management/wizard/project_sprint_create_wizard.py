# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import timedelta


class ProjectSprintCreateWizard(models.TransientModel):
    _name = "project.sprint.create.wizard"
    _description = "Create Sprint Wizard"

    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
    )
    name = fields.Char(
        string="Sprint name",
        required=True,
    )
    start_date = fields.Datetime(
        string="Start Date",
        required=True,
        default=fields.Datetime.now,
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
    end_date = fields.Datetime(
        string="End Date",
        required=True,
        compute="_compute_end_date",
        store=True,
        readonly=False,
    )
    goal = fields.Text(string="Sprint Goal")
    task_ids = fields.Many2many(
        "project.task",
        string="Select Backlog Tasks",
        domain="[('project_id', '=', project_id), ('sprint_id', '=', False)]",
    )

    @api.depends("start_date", "duration")
    def _compute_end_date(self):
        for wizard in self:
            if wizard.start_date and wizard.duration != "custom":
                weeks = int(wizard.duration)
                wizard.end_date = wizard.start_date + timedelta(weeks=weeks)
            elif not wizard.end_date:
                wizard.end_date = wizard.start_date

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "project_id" in fields_list and self.env.context.get("default_project_id"):
            res["project_id"] = self.env.context["default_project_id"]
        
        start_date = fields.Datetime.now()
        if "start_date" in fields_list:
            res["start_date"] = start_date
            
        if "name" in fields_list:
            res["name"] = self._generate_sprint_name(start_date)
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
        year = str(start_date.year)[2:]
        return f"{month} {year} (Planned)"

    @api.onchange("start_date")
    def _onchange_start_date(self):
        if self.start_date:
            self.name = self._generate_sprint_name(self.start_date)

    def action_create_sprint(self):
        self.ensure_one()
        sprint = self.env["project.sprint"].create({
            "name": self.name,
            "project_id": self.project_id.id,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "goal": self.goal,
            "state": "waiting",
        })
        if self.task_ids:
            self.task_ids.write({"sprint_id": sprint.id})
        return {"type": "ir.actions.act_window_close"}
