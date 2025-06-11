import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password


class Itinerary(models.Model):
    """しおり全体"""
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    view_password = models.CharField(max_length=128, blank=True)  # ハッシュ化
    edit_password = models.CharField(max_length=128, blank=True)  # ハッシュ化
    reset_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def set_passwords(self, view_pw: str, edit_pw: str):
        self.view_password = make_password(view_pw) if view_pw else ''
        self.edit_password = make_password(edit_pw) if edit_pw else ''

    def check_view_password(self, raw_pw: str) -> bool:
        if not self.view_password:
            return True  # パスワードが設定されていなければOK
        return check_password(raw_pw, self.view_password)

    def check_edit_password(self, raw_pw: str) -> bool:
        if not self.edit_password:
            return True  # パスワードが設定されていなければOK
        return check_password(raw_pw, self.edit_password)

    def __str__(self):
        return self.title


class TravelDate(models.Model):
    """旅程の日付"""
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name='travel_dates')
    date = models.DateField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.date} - {self.itinerary.title}"


class Schedule(models.Model):
    """日付に紐づく旅程"""
    travel_date = models.ForeignKey(TravelDate, on_delete=models.CASCADE, related_name='schedules')
    title = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    location_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.title} @ {self.location}"


class Memo(models.Model):
    """メモ（しおり単位に紐づく）"""
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name='memos')
    title = models.CharField(max_length=100)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title


class Item(models.Model):
    """持ち物リスト"""
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name='items')
    title = models.CharField(max_length=100)
    detail = models.TextField(blank=True)
    is_checked = models.BooleanField(default=False)  # チェック機能追加

    def __str__(self):
        return self.title
