/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposchatgpt;

/**
 *
 * @author kim2
 */
// Factory Method Pattern: Factory
class PaymentFactory {
    public static PaymentStrategy getPaymentMethod(String type) {
        return switch (type.toLowerCase()) {
            case "cash" -> new ByCash();
            case "credit card" -> new ByCreditCard();
            default -> throw new IllegalArgumentException("Invalid payment type.");
        };
    }
}