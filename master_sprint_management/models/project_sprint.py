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

    start_date = fields.Datetime(
        string="Start Date",
        required=True,
        tracking=True,
    )

    end_date = fields.Datetime(
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
    
    add_tasks_from_backlog = fields.Many2many(
        "project.task",
        string="Add from Backlog",
        domain="[('project_id', '=', project_id), ('sprint_id', '=', False)]",
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

    @api.onchange("add_tasks_from_backlog")
    def _onchange_add_tasks_from_backlog(self):
        if self.add_tasks_from_backlog:
            # When backlog tasks are selected, add them to task_ids
            # This is a many2many field used as a bridge
            new_tasks = self.add_tasks_from_backlog
            self.task_ids |= new_tasks
            # Reset selection after adding
            self.add_tasks_from_backlog = [(5, 0, 0)]

    # --------------------------------------------------
    # CONSTRAINTS
    # --------------------------------------------------
    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for sprint in self:
            if sprint.start_date and sprint.end_date and sprint.start_date > sprint.end_date:
                raise ValidationError(_("End date must be after start date!"))

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------
    def action_start_sprint(self):
        """Open wizard to configure and start this sprint (Jira-style)"""
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

        return {
            "name": _("Start Sprint"),
            "type": "ir.actions.act_window",
            "res_model": "project.sprint.start.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_project_id": self.project_id.id,
                "default_sprint_id": self.id,
                "default_name": self.name,
                "default_start_date": self.start_date or fields.Datetime.now(),
                "default_end_date": self.end_date,
                "default_goal": self.goal,
            },
        }

    def action_close_sprint(self):
        self.ensure_one()

        incomplete_tasks = self.task_ids.filtered(
            lambda t: not (t.stage_id and (t.stage_id.is_closed or t.stage_id.fold))
        )

        # Always open wizard (Jira-like: just ask for date)
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
                "default_close_date": fields.Date.today(),
            },
        }

    def action_view_sprint_tasks(self):
        """
        JIRA-like sprint board.
        - Domain = ONLY project
        - Sprint filter = removable search_default
        """
        self.ensure_one()

        action = {
            "name": _("Sprint Board - %s") % self.project_id.name,
            "type": "ir.actions.act_window",
            "res_model": "project.task",
            "view_mode": "kanban,tree,form",
            "views": [
                (
                    self.env.ref(
                        "master_sprint_management.view_task_kanban"
                    ).id,
                    "kanban",
                ),
                (False, "tree"),
                (False, "form"),
            ],
            "search_view_id": self.env.ref(
                "master_sprint_management.view_task_search_form"
            ).id,
            "domain": [
                ("project_id", "=", self.project_id.id),
            ],
            "context": {
                "default_project_id": self.project_id.id,
                "search_default_sprint_id": self.id,
                "group_by": "stage_id",
                "active_sprint_id": self.id,
                "active_sprint_state": self.state,
                "sprint_board_project_id": self.project_id.id,
                "create": True,
            },
        }

        # Add buttons based on sprint state
        if self.state == "active":
            action["context"]["show_close_button"] = True
        else:
            action["context"]["show_start_button"] = True

        return action

    # --------------------------------------------------
    # BUSINESS METHODS
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
