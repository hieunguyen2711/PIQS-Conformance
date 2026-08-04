/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposclaude;

/**
 *
 * @author kim2
 */
// STRATEGY PATTERN: Concrete strategy for cash payment
class CashPayment implements PaymentStrategy {
    @Override
    public void processPayment(double amount) {
        System.out.println("Processing cash payment of $" + amount);
    }
}
