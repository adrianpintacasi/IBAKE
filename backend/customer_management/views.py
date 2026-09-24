from django.shortcuts import render, get_object_or_404, redirect
from .models import Customer
from .forms import CustomerForm
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

# Create your views here.

class CustomerListView(ListView):
    model = Customer
    template_name = 'customer_management/customer_list.html'
    context_object_name = 'customers'

class CustomerCreateView(CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customer_management/customer_form.html'
    success_url = reverse_lazy('customer_management:customer_list')

class CustomerUpdateView(UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customer_management/customer_form.html'
    success_url = reverse_lazy('customer_management:customer_list')

class CustomerDeleteView(DeleteView):
    model = Customer
    template_name = 'customer_management/customer_confirm_delete.html'
    success_url = reverse_lazy('customer_management:customer_list')
