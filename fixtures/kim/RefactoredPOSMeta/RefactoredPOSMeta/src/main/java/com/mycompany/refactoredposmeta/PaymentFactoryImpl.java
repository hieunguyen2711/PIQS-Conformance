/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposmeta;

/**
 *
 * @author kim2
 */
// Factory Method Pattern: Concrete Creator
class PaymentFactoryImpl implements PaymentFactory {
    @Override
    public Payment createPayment(String paymentType) {
        switch (paymentType.toLowerCase()) {
            case "cash":
                return new ByCash();
            case "credit card":
                return new ByCreditCard();
            default:
                throw new RuntimeException("Unsupported payment type");
        }
    }
}
