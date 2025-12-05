from enum import Enum
from django.db import models
from core.models import BaseModel


class Designation(BaseModel):
    name = models.TextField()
    description = models.TextField()


class Department(BaseModel):
    name = models.TextField()
    description = models.TextField()

class LeaveTypes(str, Enum):
    SICK = "Sick Leave"
    CASUAL = "Casual Leave"
    EARNED = "Earned Leave"
    MATERNITY = "Maternity Leave"
    PATERNITY = "Paternity Leave"
    UNPAID = "Unpaid Leave"

    @classmethod
    def choices(cls):
        return [(tag, tag.value) for tag in cls]

class LeaveStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

    @classmethod
    def choices(cls):
        return [(tag, tag.value) for tag in cls]

class LeaveApplication(BaseModel):
    employee = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='leave_applications')
    leave_type = models.CharField(max_length=20, choices=LeaveTypes.choices(), default=LeaveTypes.CASUAL.value)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, default=LeaveStatus.PENDING.value)
    approved_by = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True, related_name='approved_leaves')

    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type} ({self.start_date} to {self.end_date})"

class ProjectStatuses(str, Enum):
    CREATED = "Created"
    IN_PROGRESS = "In Progress"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"

    @classmethod
    def choices(cls):
        return [(tag, tag.value) for tag in cls]

class Project(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ProjectStatuses.choices(), default=ProjectStatuses.CREATED.value)
    owner = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='owned_projects')

    def __str__(self):
        return self.name

class UserProjectMapping(BaseModel):
    user = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='project_mappings')
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='user_mappings')
    is_active = models.BooleanField(default=True)

class TaskStatuses(str, Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    DONE = "Done"

    @classmethod
    def choices(cls):
        return [(tag, tag.value) for tag in cls]

class Task(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=TaskStatuses.choices(), default=TaskStatuses.TODO.value)
    assigned_to = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='tasks')
    assigned_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='assigned_tasks', null=True, blank=True)

    def __str__(self):
        return self.title
