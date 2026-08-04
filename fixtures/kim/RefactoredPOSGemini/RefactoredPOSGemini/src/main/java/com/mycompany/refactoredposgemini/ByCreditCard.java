/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposgemini;

/**
 *
 * @author kim2
 */
class ByCreditCard implements Payment {
    private double amount;

    public ByCreditCard(double amount) {
        this.amount = amount;
    }

    @Override
    public void processPayment() {
        System.out.println("Credit card payment processed: $" + amount);
    }
}

