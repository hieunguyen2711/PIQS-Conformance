/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsclaude;

/**
 *
 * @author kim2
 */
class PaymentStrategy implements TransactionStrategy {
    @Override
    public String execute(Wallet wallet, double amount) {
        if (amount <= wallet.getBalance()) {
            wallet.setBalance(wallet.getBalance() - amount);
            wallet.addTransaction(new Transaction("Payment", amount, wallet.getBalance(), wallet.getCurrency()));
            return "Payment successful.";
        }
        return "Insufficient funds.";
    }
}
// -------------------- Strategy Pattern End --------------------
