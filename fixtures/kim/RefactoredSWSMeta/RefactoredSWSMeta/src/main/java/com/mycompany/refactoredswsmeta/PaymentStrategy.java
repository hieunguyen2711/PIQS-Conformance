/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsmeta;

/**
 *
 * @author kim2
 */
class PaymentStrategy implements TransactionStrategy {
    @Override
    public void executeTransaction(Wallet wallet, double amount) {
        wallet.makePayment(amount);
    }
}

