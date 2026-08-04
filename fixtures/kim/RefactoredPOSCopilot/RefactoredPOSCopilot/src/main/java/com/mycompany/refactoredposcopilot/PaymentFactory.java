/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposcopilot;

/**
 *
 * @author kim2
 */
// PaymentFactory (Factory Method Pattern)
class PaymentFactory {
    public static Payment createPayment(String paymentType) throws Exception {
        switch (paymentType.toLowerCase()) {
            case "cash":
                return new ByCash();
            case "credit card":
                return new ByCreditCard();
            default:
                throw new Exception("Please select a valid payment method");
        }
    }
}
