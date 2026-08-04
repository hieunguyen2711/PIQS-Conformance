/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswschatgpt;

/**
 *
 * @author kim2
 */
// Concrete Strategy for adding funds
class AddFundsStrategy implements TransactionStrategy {
    @Override
    public void execute(Transaction transaction, Wallet wallet) {
        wallet.balance += transaction.amount;
        wallet.transactions.add(transaction);
    }
}
