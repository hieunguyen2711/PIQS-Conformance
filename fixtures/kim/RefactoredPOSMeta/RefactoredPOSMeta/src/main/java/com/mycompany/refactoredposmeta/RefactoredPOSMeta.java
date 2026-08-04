/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.refactoredposmeta;

/**
 *
 * @author kim2
 */
public class RefactoredPOSMeta {

    public static void main(String[] args) {
        // Create inventory and register observer
        ItemInventory inventory = new ItemInventory();
        inventory.registerObserver(new InventoryLogger());

        // Add items to inventory
        Item item1 = new Item(1, "Milk", 3.79);
        Item item2 = new Item(2, "Banana", 1.49);
        Item item3 = new Item(3, "Apple", 5.56);
        inventory.addInventory(item1, 10);
        inventory.addInventory(item2, 50);
        inventory.addInventory(item3, 30);

        // Create sale and add items
        Sale sale = new Sale();
        sale.addComponent(new SaleLineItem(item1, 2));
        sale.addComponent(new SaleLineItem(item2, 3));
        sale.addComponent(new SaleLineItem(item3, 1));

        // Create payment factory and processor
        PaymentFactory paymentFactory = new PaymentFactoryImpl();
        Payment payment = paymentFactory.createPayment("cash");
        PaymentProcessor paymentProcessor = new PaymentProcessor(payment);

        // Process payment
        double total = sale.getSubTotal();
        paymentProcessor.processPayment(total);

        // Print receipt
        System.out.println("Receipt:");
        System.out.println("--------");
        System.out.println("Items:");
        for (SaleComponent component : sale.components) {
            SaleLineItem item = (SaleLineItem) component;
            System.out.println(item.item.getName() + " x " + item.quantity + " = $" + item.getSubTotal());
        }
        System.out.println("--------");
        System.out.println("Total: $" + total);
        System.out.println("Payment Method: " + (payment instanceof ByCash ? "Cash" : "Credit Card"));
    }
}
