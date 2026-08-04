/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package pointofsale;

import java.util.ArrayList;

/**
 *
 * @author kim2
 */

public class Register {
    private ArrayList<Sale> currentSale = new ArrayList<>();
    private ItemInventory inventory;
    private ArrayList<Receipt> receipts = new ArrayList<>();

    public Register() {
        this.inventory = new ItemInventory();
    }
    
    public String makePayment(double amount, String paymentType) throws Exception {
        System.out.println("Authorizing Payment........\n");
        Payment payment;
        
        switch (paymentType.toLowerCase()) {
            case "credit card":
                payment = new ByCreditCard(amount);
                this.Authorize((ByCreditCard)payment);
                break;
            case "cash":
                payment = new ByCash(amount);
                break;
            default:
                throw new Exception("Please select a valid payment method");
        }
        
        Receipt receipt = new Receipt(currentSale.get(currentSale.size()-1), payment);
        receipts.add(receipt);
        System.out.println(receipt);
        return "Payment received successfully";
    }
    
    public void Authorize(ByCreditCard credit) {
        System.out.println("Payment Authorized");
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
}
