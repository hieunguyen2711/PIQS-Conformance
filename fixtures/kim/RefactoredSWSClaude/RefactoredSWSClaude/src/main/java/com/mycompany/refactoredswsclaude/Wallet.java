/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsclaude;

import java.text.DecimalFormat;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;

/**
 *
 * @author kim2
 */
class Wallet {
    private double balance;
    private ArrayList<Transaction> transactions;
    private String currency;
    private Map<String, TransactionStrategy> strategies;

    public Wallet(String currency) {
        this.balance = 0.0;
        this.transactions = new ArrayList<>();
        this.currency = currency;
        this.strategies = new HashMap<>();
        strategies.put("deposit", new DepositStrategy());
        strategies.put("payment", new PaymentStrategy());
    }

    public double getBalance() { return balance; }
    public void setBalance(double balance) { this.balance = balance; }
    public String getCurrency() { return currency; }
    public void addTransaction(Transaction transaction) { transactions.add(transaction); }

    public String executeTransaction(String type, double amount) {
        TransactionStrategy strategy = strategies.get(type.toLowerCase());
        if (strategy == null) {
            return "Invalid transaction type.";
        }
        return strategy.execute(this, amount);
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

