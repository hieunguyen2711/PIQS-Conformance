/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswscopilot;

import java.text.DecimalFormat;
import java.util.ArrayList;
import java.util.List;

/**
 *
 * @author kim2
 */
class Wallet {
    private double balance;
    private ArrayList<Transaction> transactions;
    private String currency;
    private List<TransactionObserver> observers = new ArrayList<>();

    public Wallet(String currency) {
        this.balance = 0.0;
        this.transactions = new ArrayList<>();
        this.currency = currency;
    }

    // Strategy Pattern
    public String performTransaction(double amount, TransactionStrategy strategy) {
        String result = strategy.execute(amount, this);
        notifyObservers(new Transaction(strategy.getClass().getSimpleName(), amount, balance, currency));
        return result;
    }

    public double getBalance() {
        return balance;
    }

    public void setBalance(double balance) {
        this.balance = balance;
    }

    public String getCurrency() {
        return currency;
    }

    public void addTransaction(Transaction transaction) {
        transactions.add(transaction);
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

    // Observer Pattern
    public void addObserver(TransactionObserver observer) {
        observers.add(observer);
    }

    private void notifyObservers(Transaction transaction) {
        for (TransactionObserver observer : observers) {
            observer.notify(transaction);
        }
    }
}

