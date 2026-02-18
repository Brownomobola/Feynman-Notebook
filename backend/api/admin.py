from django.contrib import admin
from .models import (
    AnalysisTranscript,
    GymTranscript,
    Analysis,
    Chat,
    GymSesh,
    GymQuestions
)


@admin.register(AnalysisTranscript)
class AnalysisTranscriptAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'is_question', 'created_at')
    list_filter = ('is_question', 'created_at')
    search_fields = ('transcript', 'text_obj')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(GymTranscript)
class GymTranscriptAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('transcript', 'text_obj')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'created_at')
    list_filter = ('created_at', 'tags')
    search_fields = ('title', 'problem', 'attempt', 'explanation')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'session_key', 'title', 'tags', 'created_at')
        }),
        ('Problem & Attempt', {
            'fields': ('problem', 'attempt')
        }),
        ('Analysis Results', {
            'fields': ('praise', 'diagnosis', 'explanation')
        }),
    )


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'analysis', 'role', 'user', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(GymSesh)
class GymSeshAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'analysis', 'status', 'score', 'num_questions', 'to_percentage', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('analysis__title',)
    readonly_fields = ('created_at', 'to_percentage')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'session_key', 'analysis', 'status')
        }),
        ('Performance', {
            'fields': ('num_questions', 'score', 'to_percentage')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
    )


@admin.register(GymQuestions)
class GymQuestionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'gym_sesh', 'question_number', 'status', 'is_correct', 'is_answered', 'answered_at')
    list_filter = ('status', 'is_correct', 'is_answered', 'answered_at')
    search_fields = ('question', 'attempt', 'feedback', 'solution')
    readonly_fields = ('answered_at',)
    date_hierarchy = 'answered_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('gym_sesh', 'question_number', 'status')
        }),
        ('Question & Answer', {
            'fields': ('question', 'attempt', 'is_answered', 'answered_at')
        }),
        ('Evaluation', {
            'fields': ('is_correct', 'feedback', 'solution')
        }),
    )
