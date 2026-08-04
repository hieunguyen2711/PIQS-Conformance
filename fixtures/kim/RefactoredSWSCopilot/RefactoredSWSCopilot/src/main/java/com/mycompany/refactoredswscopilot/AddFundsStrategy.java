/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswscopilot;

/**
 *
 * @author kim2
 */
class AddFundsStrategy implements TransactionStrategy {
    @Override
    public String execute(double amount, Wallet wallet) {
        wallet.setBalance(wallet.getBalance() + amount);
        Transaction transaction = new Transaction("Deposit", amount, wallet.getBalance(), wallet.getCurrency());
        wallet.addTransaction(transaction);
        return "Funds added successfully.";
    }
}


