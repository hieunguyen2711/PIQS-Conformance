/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposgemini;

/**
 *
 * @author kim2
 */
// Strategy Pattern: Concrete Payment Implementations
class ByCash implements Payment {
    private double amount;

    public ByCash(double amount) {
        this.amount = amount;
    }

    @Override
    public void processPayment() {
        System.out.println("Cash payment processed: $" + amount);
    }
}
