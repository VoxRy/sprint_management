# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProjectSprint(models.Model):
    _name = "project.sprint"
    _description = "Project Sprint"
    _order = "start_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # --------------------------------------------------
    # BASIC
    # --------------------------------------------------
    name = fields.Char(
        string="Sprint Name",
        required=True,
        tracking=True,
    )

    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        ondelete="cascade",
        domain=[("use_sprint_management", "=", True)],
        tracking=True,
    )

    start_date = fields.Date(
        string="Start Date",
        required=True,
        tracking=True,
    )

    end_date = fields.Date(
        string="End Date",
        required=True,
        tracking=True,
    )

    goal = fields.Text(
        string="Sprint Goal",
        tracking=True,
    )

    state = fields.Selection(
        [
            ("waiting", "Waiting"),
            ("active", "Active"),
            ("closed", "Closed"),
        ],
        string="Status",
        default="waiting",
        required=True,
        tracking=True,
    )

    # --------------------------------------------------
    # TASKS
    # --------------------------------------------------
    task_ids = fields.One2many(
        "project.task",
        "sprint_id",
        string="Tasks",
    )

    task_count = fields.Integer(
        string="Tasks",
        compute="_compute_task_count",
        store=True,
    )

    # --------------------------------------------------
    # SNAPSHOT (ON CLOSE)
    # --------------------------------------------------
    snapshot_task_count = fields.Integer(
        string="Task Count (Snapshot)",
        readonly=True,
        default=0,
    )

    snapshot_done_count = fields.Integer(
        string="Done (Snapshot)",
        readonly=True,
        default=0,
    )

    snapshot_completion_percentage = fields.Float(
        string="Completion % (Snapshot)",
        readonly=True,
        default=0.0,
    )

    # --------------------------------------------------
    # DISPLAY (LIVE / SNAPSHOT)
    # --------------------------------------------------
    display_task_count = fields.Integer(
        string="Tasks",
        compute="_compute_display",
    )

    display_done_count = fields.Integer(
        string="Done",
        compute="_compute_display",
    )

    display_completion_percentage = fields.Float(
        string="Completion %",
        compute="_compute_display",
    )

    # --------------------------------------------------
    # CONSTRAINTS
    # --------------------------------------------------
    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for sprint in self:
            if sprint.start_date and sprint.end_date and sprint.start_date > sprint.end_date:
                raise ValidationError(_("End date must be after start date!"))

    # --------------------------------------------------
    # COMPUTES
    # --------------------------------------------------
    @api.depends("task_ids")
    def _compute_task_count(self):
        for sprint in self:
            sprint.task_count = len(sprint.task_ids)

    @api.depends(
        "state",
        "task_count",
        "task_ids.stage_id",
        "task_ids.stage_id.fold",
        "snapshot_task_count",
        "snapshot_done_count",
        "snapshot_completion_percentage",
    )
    def _compute_display(self):
        for sprint in self:
            if sprint.state == "closed" and sprint.snapshot_task_count:
                sprint.display_task_count = sprint.snapshot_task_count
                sprint.display_done_count = sprint.snapshot_done_count
                sprint.display_completion_percentage = sprint.snapshot_completion_percentage
                continue

            # ✅ LIVE CALC (ACTIVE / WAITING)
            done_tasks = sprint.task_ids.filtered(
                lambda t: t.stage_id and (t.stage_id.is_closed or t.stage_id.fold)
            )

            sprint.display_task_count = sprint.task_count
            sprint.display_done_count = len(done_tasks)

            if sprint.task_count:
                sprint.display_completion_percentage = round(
                    (len(done_tasks) / sprint.task_count) * 100, 2
                )
            else:
                sprint.display_completion_percentage = 0.0

    # --------------------------------------------------
    # INTERNAL
    # --------------------------------------------------
    def _compute_snapshot_values(self):
        self.ensure_one()
        total = len(self.task_ids)
        done = len(
            self.task_ids.filtered(
                lambda t: t.stage_id and (t.stage_id.is_closed or t.stage_id.fold)
            )
        )
        completion = round((done / total) * 100, 2) if total else 0.0
        return {
            "snapshot_task_count": total,
            "snapshot_done_count": done,
            "snapshot_completion_percentage": completion,
        }

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------
    def action_start_sprint(self):
        self.ensure_one()

        active_sprint = self.search(
            [
                ("project_id", "=", self.project_id.id),
                ("state", "=", "active"),
                ("id", "!=", self.id),
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

        # 🔥 AUTO CREATE STAGES (ONLY IF PROJECT USES SPRINT MGMT)
        if self.project_id.use_sprint_management:
            self.project_id._ensure_sprint_stages()

        self.write({"state": "active"})
        self.message_post(
            body=_("<p>Sprint <strong>%s</strong> has been activated.</p>") % self.name
        )
        return True

    def action_close_sprint(self):
        self.ensure_one()

        incomplete_tasks = self.task_ids.filtered(
            lambda t: not (t.stage_id and (t.stage_id.is_closed or t.stage_id.fold))
        )

        if incomplete_tasks:
            next_sprint = self.search(
                [
                    ("project_id", "=", self.project_id.id),
                    ("state", "in", ["waiting", "active"]),
                    ("id", "!=", self.id),
                    ("start_date", ">=", self.end_date),
                ],
                order="start_date",
                limit=1,
            )

            return {
                "name": _("Close Sprint"),
                "type": "ir.actions.act_window",
                "res_model": "project.sprint.close.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_sprint_id": self.id,
                    "default_next_sprint_id": next_sprint.id if next_sprint else False,
                    "default_incomplete_task_count": len(incomplete_tasks),
                    "default_action_type": "move",
                },
            }

        self.write(self._compute_snapshot_values())
        self.write({"state": "closed"})
        self.message_post(
            body=_("<p>Sprint closed successfully. All tasks were completed!</p>")
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sprint Closed"),
                "message": _("Sprint closed successfully!"),
                "type": "success",
                "sticky": False,
            },
        }

    def action_view_sprint_tasks(self):
        """
        🔥 JIRA-LIKE SPRINT BOARD
        - Domain = ONLY project
        - Sprint filter = removable search_default
        """
        self.ensure_one()

        return {
            "name": _("Sprint Board - %s") % self.project_id.name,
            "type": "ir.actions.act_window",
            "res_model": "project.task",
            "view_mode": "kanban,tree,form",
            "views": [
                (
                    self.env.ref(
                        "master_sprint_management.view_task_kanban_sprint_board"
                    ).id,
                    "kanban",
                ),
                (False, "tree"),
                (False, "form"),
            ],
            "domain": [
                ("project_id", "=", self.project_id.id),
            ],
            "context": {
                "default_project_id": self.project_id.id,
                "search_default_sprint_id": self.id,
                "group_by": "stage_id",
            },
        }
