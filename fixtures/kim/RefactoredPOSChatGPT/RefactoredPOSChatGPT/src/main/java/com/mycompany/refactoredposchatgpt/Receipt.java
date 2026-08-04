/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposchatgpt;

import java.text.DecimalFormat;

/**
 *
 * @author kim2
 */
class Receipt {
    public static void generateReceipt(Sale sale, PaymentStrategy paymentStrategy, double amount) {
        DecimalFormat df = new DecimalFormat("$##.00");
        System.out.println("\n=== RECEIPT ===");
        sale.display();
        System.out.printf("Total: %s\n", df.format(amount));
        paymentStrategy.pay(amount);
    }
}