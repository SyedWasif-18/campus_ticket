import random
from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from tickets.models import Department, Room, Ticket, Rating
from notifications.models import Notification

class Command(BaseCommand):
    help = 'Seeds the database with sample departments, rooms, users, and tickets'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting database seeding...")
        
        # 1. Clear existing non-superuser data (optional, but good for fresh seed)
        # Be careful in production, but this is a dev script
        Ticket.objects.all().delete()
        Room.objects.all().delete()
        CustomUser.objects.exclude(is_superuser=True).delete()
        Department.objects.all().delete()
        Notification.objects.all().delete()
        
        # 2. Create Departments
        depts_data = [
            {'name': 'Computer Science', 'code': 'CSE'},
            {'name': 'Electronics', 'code': 'ECE'},
            {'name': 'Mechanical', 'code': 'ME'},
            {'name': 'Administration', 'code': 'ADMIN'},
        ]
        departments = {}
        for d in depts_data:
            dept = Department.objects.create(name=d['name'], code=d['code'])
            departments[d['code']] = dept
            self.stdout.write(f"Created Department: {dept.name}")

        # 3. Create Rooms
        rooms = []
        for d_code, dept in departments.items():
            for i in range(1, 6):
                floor = str((i % 3) + 1)
                room = Room.objects.create(
                    room_number=f"{d_code}-{100 + i}",
                    floor=floor,
                    department=dept
                )
                rooms.append(room)
                # Note: The custom save() method generates the QR code automatically

        # 4. Create Users (Faculty & Attenders)
        faculty_users = []
        attender_users = []
        
        # Create 10 Faculty members
        for i in range(1, 11):
            user = CustomUser.objects.create_user(
                username=f'faculty{i}',
                password='password123',
                role='FACULTY',
                first_name=f'John{i}',
                last_name='Doe',
                email=f'faculty{i}@college.edu'
            )
            faculty_users.append(user)
            
        # Create 2 Attenders per department
        for d_code, dept in departments.items():
            for i in range(1, 3):
                user = CustomUser.objects.create_user(
                    username=f'attender_{d_code.lower()}{i}',
                    password='password123',
                    role='ATTENDER',
                    first_name=f'Attender{i}',
                    last_name=d_code,
                    department=dept
                )
                attender_users.append(user)

        self.stdout.write(f"Created {len(faculty_users)} Faculty and {len(attender_users)} Attenders.")

        # 5. Create Tickets
        categories = dict(Ticket.CATEGORY_CHOICES)
        sub_categories = [x[0] for x in Ticket.SUB_CATEGORY_CHOICES]
        statuses = [x[0] for x in Ticket.STATUS_CHOICES]
        priorities = [x[0] for x in Ticket.PRIORITY_CHOICES]
        
        for i in range(50):
            room = random.choice(rooms)
            faculty = random.choice(faculty_users)
            sub_cat = random.choice(sub_categories)
            
            # Map subcategory back to parent category (roughly)
            cat = 'SUPPLIES'
            if sub_cat in ['Projector', 'Microphone', 'Speaker', 'Smart Board', 'Computer', 'Internet']:
                cat = 'TECHNICAL'
            elif sub_cat in ['Fan', 'Lights', 'Door', 'Bench', 'Water Leakage']:
                cat = 'MAINTENANCE'

            status = random.choice(statuses)
            
            # Pick attender from the correct department if accepted or beyond
            attender = None
            if status in ['ACCEPTED', 'IN_PROGRESS', 'COMPLETED']:
                possible_attenders = [a for a in attender_users if a.department == room.department]
                if possible_attenders:
                    attender = random.choice(possible_attenders)

            ticket = Ticket.objects.create(
                faculty=faculty,
                room=room,
                category=cat,
                sub_category=sub_cat,
                priority=random.choice(priorities),
                status=status,
                description=f"Automated seed description for {sub_cat} issue in {room.room_number}.",
                attender=attender
            )
            
            # If completed, add a rating randomly (80% chance)
            if status == 'COMPLETED' and random.random() > 0.2:
                Rating.objects.create(
                    ticket=ticket,
                    score=random.randint(3, 5),
                    comments="Good service."
                )
                
        self.stdout.write(self.style.SUCCESS("Database seeded successfully with 50 tickets!"))
