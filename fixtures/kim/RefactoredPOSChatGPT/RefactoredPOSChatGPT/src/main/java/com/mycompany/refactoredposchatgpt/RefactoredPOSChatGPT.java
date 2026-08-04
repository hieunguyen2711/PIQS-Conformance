/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.refactoredposchatgpt;

import java.text.DecimalFormat;
import java.util.Scanner;

/**
 *
 * @author kim2
 */
public class RefactoredPOSChatGPT {

    public static void main(String[] args) throws Exception {
        DecimalFormat df = new DecimalFormat("$##.00");

        // Create Inventory and Attach Observers
        ItemInventory inventory = new ItemInventory();
        inventory.addObserver(new StockAlert(5));

        // Add Items to Inventory
        Item milk = new Item(1, "Milk", 3.79);
        Item banana = new Item(2, "Banana", 1.49);
        Item apple = new Item(3, "Apple", 5.56);

        inventory.addInventory(milk, 10);
        inventory.addInventory(banana, 50);
        inventory.addInventory(apple, 30);

        // Start Sale
        Sale sale = new Sale();
        sale.add(new SaleLineItem(milk, 2));
        sale.add(new SaleLineItem(banana, 3));
        sale.add(new SaleLineItem(apple, 1));

        // Display Sale
        sale.display();
        double total = sale.getSubTotal();
        System.out.printf("Total: %s\n", df.format(total));

        // Payment Process (Factory + Strategy)
        Scanner scanner = new Scanner(System.in);
        System.out.println("Select Payment Method (cash/credit card): ");
        String paymentType = scanner.nextLine();
        PaymentStrategy payment = PaymentFactory.getPaymentMethod(paymentType);

        // Generate Receipt
        Receipt.generateReceipt(sale, payment, total);
    }
}
