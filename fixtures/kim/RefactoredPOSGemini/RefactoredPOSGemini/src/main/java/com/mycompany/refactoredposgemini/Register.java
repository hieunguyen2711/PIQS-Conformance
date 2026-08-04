/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposgemini;

import java.util.ArrayList;
import java.util.List;

/**
 *
 * @author kim2
 */
class Register implements InventoryObserver {
    private ItemInventory inventory;
    private List<Sale> sales = new ArrayList<>();

    public Register(ItemInventory inventory) {
        this.inventory = inventory;
        inventory.addObserver(this);
    }

    public void makePayment(double amount, String paymentType) throws Exception {
        PaymentFactory factory;
        switch (paymentType.toLowerCase()) {
            case "credit card":
                factory = new CreditCardPaymentFactory();
                break;
            case "cash":
                factory = new CashPaymentFactory();
                break;
            default:
                throw new Exception("Please select a valid payment method");
        }

        Payment payment = factory.createPayment(amount);
        payment.processPayment();
        // ... other payment processing logic
    }

    @Override
    public void update(Item item, int newQuantity) {
        // Update the Register's internal state or trigger actions based on the new quantity
        System.out.println("Inventory updated: " + item.getName() + " quantity: " + newQuantity);
    }

    public void addSale(Sale sale) {
        sales.add(sale);
    }

    public boolean checkInventory(Item item, int quantity) {
        return inventory.checkAvailability(item, quantity);
    }
}
