import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django_ckeditor_5.fields import CKEditor5Field


def itinerary_cover_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"itinerary_covers/{instance.pk or 'new'}-{uuid.uuid4().hex}.{ext}"


class Itinerary(models.Model):
    """しおり全体"""
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    view_password = models.CharField(max_length=128, blank=True,null=True)  # ハッシュ化
    edit_password = models.CharField(max_length=128, blank=True,null=True)  # ハッシュ化
    reset_email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    total_days = models.PositiveIntegerField(blank=True, null=True)
    design_number = models.PositiveIntegerField(default=1)
    concierge_daily_limit = models.PositiveIntegerField(default=5)
    want_to_go_limit = models.PositiveIntegerField(default=30)
    qr_code = models.ImageField(upload_to="qr_codes/", blank=True)
    cover_image = models.ImageField(upload_to=itinerary_cover_upload_to, blank=True)
    cover_image_updated_on = models.DateField(blank=True, null=True)

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
    
    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.total_days = (self.end_date - self.start_date).days + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_concierge_daily_limit(self):
        return self.concierge_daily_limit or 5

    def get_want_to_go_limit(self):
        return self.want_to_go_limit or 30

#version2のスケジュールデータ
# models.py

class ScheduleV2(models.Model):
    ICON_DEFAULT = "default"
    ICON_FOOD = "food"
    ICON_MOVE = "move"
    ICON_PHOTO = "photo"
    ICON_STAY = "stay"
    ICON_SHOPPING = "shopping"
    ICON_EVENT = "event"
    ICON_FLAG = "flag"
    ICON_FLIGHT = "flight"
    ICON_CAR = "car"

    ICON_CHOICES = [
        (ICON_DEFAULT, "通常"),
        (ICON_FOOD, "食事"),
        (ICON_MOVE, "移動"),
        (ICON_PHOTO, "観光"),
        (ICON_STAY, "宿泊"),
        (ICON_SHOPPING, "買い物"),
        (ICON_EVENT, "イベント"),
        (ICON_FLAG, "フラグ"),
        (ICON_FLIGHT, "飛行機"),
        (ICON_CAR, "車"),
    ]

    ICON_CLASS_MAP = {
        ICON_DEFAULT: "fa-circle",
        ICON_FOOD: "fa-utensils",
        ICON_MOVE: "fa-train-subway",
        ICON_PHOTO: "fa-camera",
        ICON_STAY: "fa-bed",
        ICON_SHOPPING: "fa-cart-shopping",
        ICON_EVENT: "fa-star",
        ICON_FLAG: "fa-flag",
        ICON_FLIGHT: "fa-plane",
        ICON_CAR: "fa-car",
    }

    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name="schedules"
    )
    date = models.DateField()
    day_index = models.PositiveIntegerField(blank=True, null=True)
    title = models.CharField(max_length=30)   # 要件に合わせる
    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default=ICON_DEFAULT)
    description = models.TextField(blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    place = models.ForeignKey(
        "WantToGo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="schedules"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["date", "order"]

    def __str__(self):
        return f"{self.date} {self.title}"

    def get_icon_class(self):
        return self.ICON_CLASS_MAP.get(self.icon, self.ICON_CLASS_MAP[self.ICON_DEFAULT])

    def get_title_color_class(self):
        valid_icons = {choice[0] for choice in self.ICON_CHOICES}
        icon = self.icon if self.icon in valid_icons else self.ICON_DEFAULT
        return f"schedule-title-{icon}"


class WantToGo(models.Model):
    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name="want_to_go_list"
    )

    # Google由来でも手入力でも作れるようにする
    place_id = models.CharField(max_length=200, blank=True, default="")
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    rating = models.FloatField(null=True, blank=True)

    memo = models.TextField(blank=True)
    planned_day = models.IntegerField(default=0)
    stay_minutes = models.IntegerField(null=True, blank=True)
    priority = models.IntegerField(default=3)
    tag = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class MemoV2(models.Model):
    itinerary = models.OneToOneField(Itinerary, on_delete=models.CASCADE, related_name="memo_v2")
    content = CKEditor5Field(config_name="default", blank=True)

    def __str__(self):
        return f"Memo for {self.itinerary}"


class ChecklistV2(models.Model):
    itinerary = models.OneToOneField(Itinerary, on_delete=models.CASCADE, related_name="checklist_v2")
    content = models.TextField(blank=True, default="[]")

    def __str__(self):
        return f"Checklist for {self.itinerary}"


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


class ConciergeChatLog(models.Model):
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name="concierge_logs")
    conversation_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    turn_index = models.PositiveIntegerField(default=1)
    user_message = models.TextField()
    moderation_prompt = models.TextField(blank=True)
    moderation_result = models.JSONField(default=dict, blank=True)
    data_selection_prompt = models.TextField(blank=True)
    data_selection_result = models.JSONField(default=dict, blank=True)
    answer_prompt = models.TextField(blank=True)
    answer_context = models.JSONField(default=dict, blank=True)
    assistant_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["conversation_id", "turn_index", "id"]

    def __str__(self):
        return f"Concierge log {self.itinerary_id} #{self.turn_index}"
