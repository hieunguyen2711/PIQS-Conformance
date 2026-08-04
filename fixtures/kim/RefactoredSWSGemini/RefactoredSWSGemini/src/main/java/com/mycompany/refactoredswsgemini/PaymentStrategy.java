/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsgemini;

/**
 *
 * @author kim2
 */
// Payment Strategy
class PaymentStrategy implements TransactionStrategy {
    @Override
    public void execute(Wallet wallet, double amount) {
        if (amount <= wallet.balance) {
            wallet.balance -= amount;
            wallet.transactions.add(new Transaction("Payment", amount, wallet.balance, wallet.currency));
        } else {
            throw new RuntimeException("Insufficient funds."); 
        }
    }
}
