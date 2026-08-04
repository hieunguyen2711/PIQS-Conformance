/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsclaude;

/**
 *
 * @author kim2
 */
class DepositStrategy implements TransactionStrategy {
    @Override
    public String execute(Wallet wallet, double amount) {
        wallet.setBalance(wallet.getBalance() + amount);
        wallet.addTransaction(new Transaction("Deposit", amount, wallet.getBalance(), wallet.getCurrency()));
        return "Deposit successful.";
    }
}
