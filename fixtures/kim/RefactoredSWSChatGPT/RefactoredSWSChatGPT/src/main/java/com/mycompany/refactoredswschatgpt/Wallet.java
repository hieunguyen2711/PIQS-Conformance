/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswschatgpt;

import java.text.DecimalFormat;
import java.util.ArrayList;

/**
 *
 * @author kim2
 */
class Wallet {
    double balance;
    ArrayList<Transaction> transactions;
    String currency;

    public Wallet(String currency) {
        this.balance = 0.0;
        this.transactions = new ArrayList<>();
        this.currency = currency;
    }

    public void processTransaction(double amount, String type, TransactionStrategy strategy) {
        Transaction transaction = new Transaction(type, amount, currency, strategy);
        transaction.strategy.execute(transaction, this);
    }

    public void showBalance() {
        DecimalFormat df = new DecimalFormat("$##0.00");
        System.out.println("Current Balance in " + currency + ": " + df.format(balance));
    }

    public void showTransactions() {
        for (Transaction t : transactions) {
            System.out.println(t);
        }
    }
}
