/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposchatgpt;

/**
 *
 * @author kim2
 */
// Strategy Pattern: Concrete Strategy (Credit Card)
class ByCreditCard implements PaymentStrategy {
    @Override
    public void pay(double amount) {
        System.out.printf("Paid %.2f by Credit Card.\n", amount);
    }
}
