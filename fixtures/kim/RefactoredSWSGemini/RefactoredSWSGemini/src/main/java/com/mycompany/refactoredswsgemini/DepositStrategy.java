/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsgemini;

/**
 *
 * @author kim2
 */
// Deposit Strategy
class DepositStrategy implements TransactionStrategy {
    @Override
    public void execute(Wallet wallet, double amount) {
        wallet.balance += amount;
        wallet.transactions.add(new Transaction("Deposit", amount, wallet.balance, wallet.currency));
    }
}
