/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposclaude;

import java.util.ArrayList;
import java.util.List;

/**
 *
 * @author kim2
 */
class Register {
    private List<Sale> sales = new ArrayList<>();
    private ItemInventory inventory;

    public Register() {
        this.inventory = new ItemInventory();
        this.inventory.addObserver(new InventoryAlert(5));  // Alert when inventory drops below 5
    }
    
    public void addInventory(Item item, int quantity) {
        inventory.addInventory(item, quantity);
    }
    
    public boolean checkInventory(Item item, int quantity) {
        return inventory.checkAvailability(item, quantity);
    }
    
    public void updateInventory(Item item, int quantity) {
        inventory.updateInventory(item, quantity);
    }
    
    public void addSale(Sale sale) {
        sales.add(sale);
    }
    
    // FACTORY METHOD PATTERN: Using factory to create payment strategy
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
                throw new Exception("Invalid payment type");
        }
        PaymentStrategy paymentStrategy = factory.createPayment();
        paymentStrategy.processPayment(amount);
    }
}
