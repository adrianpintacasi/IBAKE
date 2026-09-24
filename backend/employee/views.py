from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Employee
from .forms import EmployeeForm

class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'employee/employee_list.html'
    context_object_name = 'employees'

class EmployeeCreateView(LoginRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee/employee_form.html'
    success_url = reverse_lazy('employee:employee_list')

class EmployeeUpdateView(LoginRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee/employee_form.html'
    success_url = reverse_lazy('employee:employee_list')

class EmployeeDeleteView(LoginRequiredMixin, DeleteView):
    model = Employee
    template_name = 'employee/employee_confirm_delete.html'
    success_url = reverse_lazy('employee:employee_list') 