# Insurance Management Module for Odoo

A comprehensive insurance agency management system built on Odoo that allows insurance agencies to manage their customers, policies, quotations, and payments.

## Features

- **Customer Management**: Store customer information with insurance-specific fields like tax ID, profession, and assigned insurance agent
- **Policy Management**: Create and track insurance policies with vehicle details, coverage options, and policy statuses
- **Quotation to Policy Workflow**: Leverages Odoo's standard quotation-to-order workflow for creating insurance policies
- **Premium Calculation**: Automatically calculate premiums based on selected coverage options
- **Payment Tracking**: Manage policy payments with support for different payment frequencies and installment plans
- **Reporting**: Analyze policy and payment data with built-in reporting tools

## Installation

1. Copy the module to your Odoo addons directory
2. Restart your Odoo server
3. Go to Apps menu and click "Update Apps List"
4. Search for "Insurance Management" and install the module

## Configuration

After installation:

1. Set up your insurance agents as partners with the "Is Insurance Agent" checkbox enabled
2. Create insurance products and update premium calculation logic as needed

## Usage

The module adds a new "Insurance" application to your Odoo menu with the following sections:

- **Dashboard**: Overview of all insurance policies
- **Operations**: Manage quotations, policies, and payments
- **Partners**: Manage customers and insurance agents
- **Reporting**: Analyze policy data
- **Configuration**: Configure module settings

## License

LGPL-3