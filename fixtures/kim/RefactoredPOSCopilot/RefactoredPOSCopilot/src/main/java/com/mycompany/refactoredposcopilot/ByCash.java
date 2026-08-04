/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposcopilot;

/**
 *
 * @author kim2
 */
class ByCash implements Payment {
    @Override
    public void pay(double amount) {
        System.out.println("Paid " + amount + " by Cash.");
    }
}
