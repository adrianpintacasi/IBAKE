from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from employee.models import Employee

User = get_user_model()

class Command(BaseCommand):
    help = 'Create user accounts for employees and link them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--employee-id',
            type=str,
            help='Create user for specific employee ID',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='password123',
            help='Default password for created users (default: password123)',
        )

    def handle(self, *args, **options):
        employee_id = options.get('employee_id')
        default_password = options.get('password')

        if employee_id:
            try:
                employee = Employee.objects.get(employee_id=employee_id)
                self.create_user_for_employee(employee, default_password)
            except Employee.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Employee with ID {employee_id} not found')
                )
        else:
            employees_without_users = Employee.objects.filter(
                employeeuser__isnull=True,
                is_active=True
            )
            
            if not employees_without_users.exists():
                self.stdout.write(
                    self.style.SUCCESS('All active employees already have user accounts')
                )
                return

            self.stdout.write(f'Creating users for {employees_without_users.count()} employees...')
            
            for employee in employees_without_users:
                self.create_user_for_employee(employee, default_password)

    def create_user_for_employee(self, employee, password):
        username = employee.employee_id.lower()
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'Username {username} already exists, skipping {employee.full_name}')
            )
            return

        user = User.objects.create_user(
            username=username,
            email=employee.email,
            password=password,
            first_name=employee.first_name,
            last_name=employee.last_name,
            employee=employee
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Created user "{username}" for {employee.full_name} ({employee.position})'
            )
        )
        
        self.stdout.write(
            self.style.WARNING(
                f'  Login credentials: Username: {username}, Password: {password}'
            )
        ) 