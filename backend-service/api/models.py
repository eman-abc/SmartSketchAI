# api/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('forensic', 'Forensic User'),
        ('editor', 'Attribute Editor'),
        ('general', 'General User'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='general')
    email_verified = models.BooleanField(default=False)
    # optionally add profile fields
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

class GeneratedImage(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='generated_images', null=True, blank=True)
    prompt = models.TextField()
    image_file = models.ImageField(upload_to='generated/', null=True, blank=True)
    generation_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    seed = models.BigIntegerField(null=True, blank=True)
    model_version = models.CharField(max_length=50, blank=True)
    forensic_hash = models.CharField(max_length=64, blank=True, null=True, help_text="SHA-256 hash of the pixel data")
    is_watermarked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GeneratedImage {self.id} by {self.user.username}"

class EditedImage(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='edited_images', null=True, blank=True)
    original_image = models.ForeignKey(GeneratedImage, on_delete=models.CASCADE, related_name='edits', null=True, blank=True)
    edit_prompt = models.TextField()
    edited_file = models.ImageField(upload_to='edited/')
    forensic_hash = models.CharField(max_length=64, blank=True, null=True, help_text="SHA-256 hash of the pixel data")
    is_watermarked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class ImageScore(models.Model):
    image = models.ForeignKey(GeneratedImage, on_delete=models.CASCADE, null=True, blank=True)
    edited_image = models.ForeignKey(EditedImage, on_delete=models.CASCADE, null=True, blank=True)
    clip_score = models.FloatField(null=True, blank=True)
    identity_score = models.FloatField(null=True, blank=True)
    final_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ForensicCritique(models.Model):
    image = models.ForeignKey(GeneratedImage, on_delete=models.CASCADE, related_name='critiques', null=True, blank=True)
    edited_image = models.ForeignKey(EditedImage, on_delete=models.CASCADE, related_name='critiques', null=True, blank=True)
    model_name = models.CharField(max_length=255, blank=True)
    decision = models.CharField(max_length=20, default='accept')
    score = models.FloatField(null=True, blank=True)
    issues = models.JSONField(default=list, blank=True)
    matched_features = models.JSONField(default=list, blank=True)
    missing_features = models.JSONField(default=list, blank=True)
    prompt_adjustment = models.TextField(blank=True)
    safety_flags = models.JSONField(default=list, blank=True)
    reasoning_summary = models.TextField(blank=True)
    raw_report = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AuditLog(models.Model):
    ACTIONS = (
        ('generate', 'Generate'),
        ('edit', 'Edit'),
        ('view', 'View'),
        ('login', 'Login'),
    )
    user = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTIONS)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    prompt_used = models.TextField(null=True, blank=True)
    image = models.ForeignKey(GeneratedImage, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class ForensicRequest(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)
    reason = models.TextField(null=True, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)


class AgentCheckpoint(models.Model):
    """
    Technical model to store LangGraph state checkpoints.
    Used by DjangoCheckpointer to persist agent state.
    """
    thread_id = models.CharField(max_length=255, db_index=True)
    checkpoint_id = models.CharField(max_length=255, db_index=True)
    parent_id = models.CharField(max_length=255, null=True, blank=True)
    checkpoint_data = models.BinaryField(help_text="Pickled LangGraph Checkpoint")
    metadata_data = models.BinaryField(help_text="Pickled LangGraph Metadata")
    version = models.IntegerField(default=1, help_text="Schema version for forward compatibility")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('thread_id', 'checkpoint_id')
        ordering = ['-created_at']

    def __str__(self):
        return f"Checkpoint {self.checkpoint_id} for Thread {self.thread_id}"

class AgentStateWrite(models.Model):
    """
    Stores intermediate writes for a checkpoint task.
    Required by newer LangGraph versions for robust state management.
    """
    thread_id = models.CharField(max_length=255, db_index=True)
    checkpoint_id = models.CharField(max_length=255, db_index=True)
    task_id = models.CharField(max_length=255)
    idx = models.IntegerField()
    channel = models.CharField(max_length=255)
    value = models.BinaryField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('thread_id', 'checkpoint_id', 'task_id', 'idx')

class Conversation(models.Model):
    """
    Business model representing a forensic investigation session.
    """
    thread_id = models.CharField(max_length=255, unique=True, db_index=True)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='conversations')
    case_number = models.CharField(max_length=100, blank=True, null=True)
    suspect_name_guess = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Case {self.case_number or self.id} ({self.user.username})"
