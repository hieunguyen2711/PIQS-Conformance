/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswschatgpt;

/**
 *
 * @author kim2
 */
// Concrete Strategy for making payments
class MakePaymentStrategy implements TransactionStrategy {
    @Override
    public void execute(Transaction transaction, Wallet wallet) {
        if (transaction.amount <= wallet.balance) {
            wallet.balance -= transaction.amount;
            wallet.transactions.add(transaction);
        } else {
            throw new IllegalArgumentException("Insufficient funds.");
        }
    }
}
