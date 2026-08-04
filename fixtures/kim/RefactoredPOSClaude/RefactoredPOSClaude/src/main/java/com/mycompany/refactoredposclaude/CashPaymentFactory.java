/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposclaude;

/**
 *
 * @author kim2
 */
// FACTORY METHOD PATTERN: Concrete factories for each payment type
class CashPaymentFactory implements PaymentFactory {
    @Override
    public PaymentStrategy createPayment() {
        return new CashPayment();
    }
}