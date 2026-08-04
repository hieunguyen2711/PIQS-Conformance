/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposgemini;

/**
 *
 * @author kim2
 */
class CreditCardPaymentFactory implements PaymentFactory {
    @Override
    public Payment createPayment(double amount) {
        return new ByCreditCard(amount);
    }
}
