from django.db import models

class SeatingArrangement(models.Model):
    room_number = models.IntegerField()
    bench_number = models.IntegerField()
    student1 = models.CharField(max_length=20, blank=True, null=True)
    student2 = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Room {self.room_number} - Bench {self.bench_number}"
