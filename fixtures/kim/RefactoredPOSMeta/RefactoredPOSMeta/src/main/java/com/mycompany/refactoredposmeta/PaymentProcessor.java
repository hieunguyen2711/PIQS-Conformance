/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposmeta;

/**
 *
 * @author kim2
 */
// Strategy Pattern: Context
class PaymentProcessor {
    private Payment paymentStrategy;

    public PaymentProcessor(Payment paymentStrategy) {
        this.paymentStrategy = paymentStrategy;
    }

    public void processPayment(double amount) {
        paymentStrategy.processPayment(amount);
    }
}   