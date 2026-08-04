/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposmeta;

/**
 *
 * @author kim2
 */
// Factory Method Pattern: Concrete Products
class ByCash implements Payment {
    @Override
    public void processPayment(double amount) {
        System.out.println("Processing cash payment of $" + amount);
    }
}