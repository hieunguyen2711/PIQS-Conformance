/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsgemini;

import java.text.DecimalFormat;
import java.util.ArrayList;

/**
 *
 * @author kim2
 */
// Wallet class with Strategy Pattern applied to transactions
class Wallet {
    private double balance;
    private ArrayList<Transaction> transactions;
    private String currency;
    private TransactionStrategy transactionStrategy;

    public Wallet(String currency, TransactionStrategy strategy) {
        this.balance = 0.0;
        this.transactions = new ArrayList<>();
        this.currency = currency;
        this.transactionStrategy = strategy;
    }

    public void addFunds(double amount) {
        transactionStrategy.execute(this, amount);
    }

    public String makePayment(double amount) {
        try {
            transactionStrategy.execute(this, amount);
            return "Payment successful.";
        } catch (RuntimeException e) {
            return e.getMessage(); 
        }
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
