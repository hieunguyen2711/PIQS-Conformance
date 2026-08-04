/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposcopilot;

import java.util.ArrayList;
import java.util.List;

/**
 *
 * @author kim2
 */
// Register class modified for Factory Method and Strategy Patterns
class Register implements InventoryObserver {
    private List<Sale> currentSale = new ArrayList<>();
    private ItemInventory inventory;
    private List<Receipt> receipts = new ArrayList<>();

    public Register() {
        this.inventory = new ItemInventory();
        this.inventory.addObserver(this);
    }

    public String makePayment(double amount, String paymentType) throws Exception {
        System.out.println("Authorizing Payment........\n");
        Payment payment = PaymentFactory.createPayment(paymentType);
        payment.pay(amount);

        Receipt receipt = new Receipt(currentSale.get(currentSale.size()-1), payment);
        receipts.add(receipt);
        System.out.println(receipt);
        return "Payment received successfully";
    }

    public void addSale(Sale s) {
        currentSale.add(s);
    }

    public void addInventory(Item item, int quantity) {
        inventory.addInventory(item, quantity);
    }

    public boolean checkInventory(Item item, int quantity) {
        return inventory.checkAvailability(item, quantity);
    }

    @Override
    public void update(Item item, int quantity) {
        System.out.println("Inventory updated: " + item.getName() + " - " + quantity);
    }
}
